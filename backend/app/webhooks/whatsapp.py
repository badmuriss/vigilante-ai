"""Inbound WhatsApp webhook — the second channel into the conversational HUB.

GET  /api/webhooks/whatsapp  -> Meta verification handshake (verify token).
POST /api/webhooks/whatsapp  -> inbound messages, HMAC-verified, dispatched to
                                the SAME ChatService the web UI uses.

Tenant is resolved from `phone_number_id` in the Meta payload. The signature
is checked against the tenant's decrypted `app_secret`. Processing happens in
a background task so we return 200 fast (Meta retries on non-2xx).
"""

from __future__ import annotations

import hashlib
import hmac
import json

import structlog
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.chat import service
from app.config import settings
from app.db.base import get_session, session_scope
from app.db.entities import WhatsAppConfig
from app.integrations import whisper
from app.observability import wa_signature_failures_total, wa_webhook_received_total
from app.services.crypto import SecretDecryptError, decrypt_secret, encryption_available
from app.services.whatsapp_notifier import download_media, send_session_text
from app.chat.prompts import split_for_whatsapp, strip_markdown

log = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])


@router.get("/whatsapp")
def verify_webhook(
    hub_mode: str = Query("", alias="hub.mode"),
    hub_verify_token: str = Query("", alias="hub.verify_token"),
    hub_challenge: str = Query("", alias="hub.challenge"),
    session: Session = Depends(get_session),
) -> PlainTextResponse:
    if hub_mode != "subscribe":
        raise HTTPException(status_code=400, detail="Invalid hub.mode")
    if not encryption_available():
        raise HTTPException(status_code=503, detail="Encryption key not configured")

    configs = session.scalars(
        select(WhatsAppConfig).where(
            WhatsAppConfig.webhook_verify_token_encrypted.is_not(None)
        )
    ).all()
    for cfg in configs:
        try:
            token = decrypt_secret(cfg.webhook_verify_token_encrypted or "")
        except SecretDecryptError:
            continue
        if hmac.compare_digest(token, hub_verify_token):
            return PlainTextResponse(hub_challenge)
    raise HTTPException(status_code=403, detail="Verification token mismatch")


def _phone_number_id(payload: dict) -> str | None:
    try:
        return (
            payload["entry"][0]["changes"][0]["value"]["metadata"]["phone_number_id"]
        )
    except (KeyError, IndexError, TypeError):
        return None


@router.post("/whatsapp")
async def receive_webhook(
    request: Request,
    background: BackgroundTasks,
    session: Session = Depends(get_session),
) -> dict:
    raw = await request.body()
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    pnid = _phone_number_id(payload)
    cfg = (
        session.scalar(
            select(WhatsAppConfig).where(WhatsAppConfig.phone_number_id == pnid)
        )
        if pnid
        else None
    )
    if cfg is None:
        wa_webhook_received_total.labels(kind="unknown_tenant").inc()
        log.warning("wa_unknown_phone_number_id", phone_number_id=pnid)
        return {"received": True}  # 200 so Meta stops retrying an unconfigured number

    # Signature check (HMAC-SHA256 of raw body with the tenant's app secret).
    if not _signature_ok(cfg, raw, request.headers.get("x-hub-signature-256", "")):
        wa_signature_failures_total.inc()
        log.warning("wa_signature_mismatch", phone_number_id=pnid)
        raise HTTPException(status_code=403, detail="Invalid signature")

    tenant_id = cfg.tenant_id
    cfg_id = cfg.id
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            for msg in value.get("messages", []) or []:
                background.add_task(_process_message, tenant_id, cfg_id, msg)

    return {"received": True}


def _signature_ok(cfg: WhatsAppConfig, raw: bytes, header: str) -> bool:
    if not cfg.app_secret_encrypted or not encryption_available():
        # No app secret configured -> cannot verify; reject to be safe.
        return False
    try:
        secret = decrypt_secret(cfg.app_secret_encrypted)
    except SecretDecryptError:
        return False
    expected = "sha256=" + hmac.new(
        secret.encode("utf-8"), raw, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, header)


def _process_message(tenant_id: str, cfg_id: str, msg: dict) -> None:
    """Background worker: transcribe if needed, run the agent, reply on WA."""
    wa_id = msg.get("from", "")
    msg_type = msg.get("type")

    if msg_type == "text":
        text = msg.get("text", {}).get("body", "")
        wa_webhook_received_total.labels(kind="text").inc()
    elif msg_type == "audio":
        media_id = msg.get("audio", {}).get("id")
        mime = msg.get("audio", {}).get("mime_type", "audio/ogg")
        audio = download_media(media_id, cfg_id) if media_id else None
        text = whisper.transcribe(audio or b"", mime_type=mime)
        wa_webhook_received_total.labels(kind="audio").inc()
    else:
        wa_webhook_received_total.labels(kind="unsupported").inc()
        text = "[mensagem não suportada]"

    if not wa_id or not text.strip():
        return

    try:
        with session_scope() as session:
            reply = service.handle_message(
                session,
                tenant_id=tenant_id,
                channel="whatsapp",
                user_identifier=wa_id,
                text=text,
            )
            session.commit()
            content = reply.content
    except Exception:  # noqa: BLE001
        log.exception("wa_chat_failed", tenant_id=tenant_id, wa_id=wa_id)
        content = "Desculpe, tive um problema ao processar sua mensagem. Tente novamente."

    # WhatsApp gets plain text (markdown stripped); the UI keeps the raw markdown.
    plain = strip_markdown(content)
    for segment in split_for_whatsapp(plain, max_chars=settings.WA_MAX_SEGMENT_CHARS):
        result = send_session_text(cfg_id, to=wa_id, body=segment)
        if not result.get("ok"):
            log.warning("wa_reply_failed", wa_id=wa_id, error=result.get("error"))
