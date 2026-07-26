"""Inbound WhatsApp webhook — the second channel into the conversational HUB.

GET  /api/webhooks/whatsapp  -> Meta verification handshake (verify token).
POST /api/webhooks/whatsapp  -> inbound messages, HMAC-verified, dispatched to
                                the SAME ChatService the web UI uses.

There is ONE shared platform WhatsApp number, so the tenant cannot be resolved
from `phone_number_id` anymore. Instead it is resolved from the SENDER's phone
(`msg.from`) via the `whatsapp_operators` table — each operator phone belongs
to exactly one tenant. The signature is checked against the global app secret.
Processing happens in a background task so we return 200 fast (Meta retries on
non-2xx).
"""

from __future__ import annotations

import hashlib
import hmac
import json
from datetime import datetime

import structlog
from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse
from sqlalchemy import select

from app.chat import service
from app.config import settings
from app.db.base import session_scope
from app.db.entities import Alert, Camera, Site
from app.integrations import whisper
from app.observability import wa_signature_failures_total, wa_webhook_received_total
from app.repositories import WhatsAppOperatorRepository
from app.services.whatsapp_notifier import download_media, send_session_text, to_e164
from app.chat.prompts import split_for_whatsapp, strip_markdown

log = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])


def _safe_eq(a: str, b: str) -> bool:
    """Constant-time compare that never raises on attacker-controlled input.

    `hmac.compare_digest` raises TypeError when a str arg holds non-ASCII
    codepoints; a malicious verify token / signature header would otherwise
    surface as a 500. Treat any such input as a non-match.
    """
    try:
        return hmac.compare_digest(a, b)
    except (TypeError, ValueError):
        return False


@router.get("/whatsapp")
def verify_webhook(
    hub_mode: str = Query("", alias="hub.mode"),
    hub_verify_token: str = Query("", alias="hub.verify_token"),
    hub_challenge: str = Query("", alias="hub.challenge"),
) -> PlainTextResponse:
    if hub_mode != "subscribe":
        raise HTTPException(status_code=400, detail="Invalid hub.mode")
    expected = settings.WHATSAPP_VERIFY_TOKEN
    if not expected:
        raise HTTPException(status_code=503, detail="Verify token not configured")
    if _safe_eq(expected, hub_verify_token):
        return PlainTextResponse(hub_challenge)
    raise HTTPException(status_code=403, detail="Verification token mismatch")


@router.post("/whatsapp")
async def receive_webhook(
    request: Request,
    background: BackgroundTasks,
) -> dict:
    raw = await request.body()
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    # Signature check (HMAC-SHA256 of raw body with the global app secret).
    if not _signature_ok(raw, request.headers.get("x-hub-signature-256", "")):
        wa_signature_failures_total.inc()
        log.warning("wa_signature_mismatch")
        raise HTTPException(status_code=403, detail="Invalid signature")

    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            for msg in value.get("messages", []) or []:
                background.add_task(_process_message, msg)

    return {"received": True}


def _signature_ok(raw: bytes, header: str) -> bool:
    secret = settings.WHATSAPP_APP_SECRET
    if not secret:
        # No app secret configured -> cannot verify; reject to be safe.
        return False
    expected = "sha256=" + hmac.new(
        secret.encode("utf-8"), raw, hashlib.sha256
    ).hexdigest()
    return _safe_eq(expected, header)


def _process_message(msg: dict) -> None:
    """Background worker: resolve tenant by sender, run the agent, reply on WA."""
    wa_id = msg.get("from", "")
    msg_type = msg.get("type")

    if not wa_id:
        return

    # Resolve the tenant this sender acts on behalf of. Unknown number -> drop.
    with session_scope() as session:
        tenant_id = WhatsAppOperatorRepository(session).find_tenant_id_by_phone(
            to_e164(wa_id)
        )
    if tenant_id is None:
        wa_webhook_received_total.labels(kind="unknown_operator").inc()
        log.warning("wa_unknown_operator", wa_id=wa_id)
        return

    # Quick-reply button tap on a review alert -> apply the operator's decision.
    if msg_type == "button":
        wa_webhook_received_total.labels(kind="button").inc()
        payload = (msg.get("button") or {}).get("payload", "")
        _handle_review_button(tenant_id, wa_id, payload)
        return

    if msg_type == "text":
        text = msg.get("text", {}).get("body", "")
        wa_webhook_received_total.labels(kind="text").inc()
    elif msg_type == "audio":
        media_id = msg.get("audio", {}).get("id")
        mime = msg.get("audio", {}).get("mime_type", "audio/ogg")
        audio = download_media(media_id) if media_id else None
        text = whisper.transcribe(audio or b"", mime_type=mime)
        wa_webhook_received_total.labels(kind="audio").inc()
    else:
        wa_webhook_received_total.labels(kind="unsupported").inc()
        text = "[mensagem não suportada]"

    if not text.strip():
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
        result = send_session_text(to=wa_id, body=segment)
        if not result.get("ok"):
            log.warning("wa_reply_failed", wa_id=wa_id, error=result.get("error"))


def _handle_review_button(tenant_id: str, wa_id: str, payload: str) -> None:
    """Apply an operator's review decision from a quick-reply button.

    Payload is `confirm:<alert_id>` or `false_positive:<alert_id>`. The alert
    must belong to the operator's tenant. Idempotent: a second tap on an
    already-reviewed alert just reports the current state.
    """
    action, _, alert_id = payload.partition(":")
    feedback = {"confirm": "correct", "false_positive": "false_positive"}.get(action)
    if feedback is None or not alert_id:
        send_session_text(to=wa_id, body="Não entendi essa ação.")
        return

    with session_scope() as session:
        alert = session.get(Alert, alert_id)
        if alert is None:
            send_session_text(to=wa_id, body="Alerta não encontrado.")
            return
        owner = session.scalar(
            select(Site.tenant_id)
            .join(Camera, Camera.site_id == Site.id)
            .where(Camera.id == alert.camera_id)
        )
        if str(owner) != str(tenant_id):
            log.warning("wa_button_wrong_tenant", wa_id=wa_id, alert_id=alert_id)
            send_session_text(to=wa_id, body="Você não tem acesso a este alerta.")
            return
        if alert.feedback in ("correct", "false_positive"):
            done = (
                "confirmada" if alert.feedback == "correct" else "marcada como falso positivo"
            )
            send_session_text(to=wa_id, body=f"Este alerta já foi revisado ({done}).")
            return
        alert.feedback = feedback
        alert.feedback_at = datetime.utcnow()
        session.commit()
        try:
            from app.main import retraining_exporter

            session.refresh(alert)
            retraining_exporter.export(alert)
        except Exception:  # noqa: BLE001
            log.exception("wa_retrain_export_failed", alert_id=alert_id)

    body = (
        "✅ Infração confirmada. Obrigado!"
        if feedback == "correct"
        else "✅ Marcado como falso positivo. Obrigado!"
    )
    send_session_text(to=wa_id, body=body)
