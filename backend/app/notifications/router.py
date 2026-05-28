"""Notification integration config endpoints.

Per-tenant config + a test-send endpoint reviewers can use to confirm
the provider credentials work before turning notifications on. All endpoints
require role `admin` because stored webhook URLs and tokens are sensitive.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.dependencies import CurrentUser, require_role
from app.db.base import get_session
from app.notifications.schemas import (
    TeamsConfigResponse,
    TeamsConfigUpdateRequest,
    TeamsTestResponse,
    WhatsAppConfigResponse,
    WhatsAppConfigUpdateRequest,
    WhatsAppTestRequest,
    WhatsAppTestResponse,
)
from app.repositories import TeamsConfigRepository, WhatsAppConfigRepository
from app.services.crypto import (
    EncryptionUnavailableError,
    encrypt_secret,
    encryption_available,
)

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


_ADMIN_ONLY = require_role("admin")


def _to_response(cfg) -> WhatsAppConfigResponse:  # type: ignore[no-untyped-def]
    if cfg is None:
        return WhatsAppConfigResponse(
            enabled=False,
            phone_number_id=None,
            has_token=False,
            template_name=None,
            template_language="pt_BR",
            recipients=[],
            include_image=True,
        )
    return WhatsAppConfigResponse(
        enabled=cfg.enabled,
        phone_number_id=cfg.phone_number_id,
        has_token=bool(cfg.access_token_encrypted),
        template_name=cfg.template_name,
        template_language=cfg.template_language,
        recipients=list(cfg.recipients or []),
        include_image=cfg.include_image,
    )


def _to_teams_response(cfg) -> TeamsConfigResponse:  # type: ignore[no-untyped-def]
    if cfg is None:
        return TeamsConfigResponse(
            enabled=False,
            has_webhook_url=False,
            channel_name=None,
            notify_on_confirmed=True,
        )
    return TeamsConfigResponse(
        enabled=cfg.enabled,
        has_webhook_url=bool(cfg.webhook_url_encrypted),
        channel_name=cfg.channel_name,
        notify_on_confirmed=cfg.notify_on_confirmed,
    )


@router.get("/whatsapp", response_model=WhatsAppConfigResponse)
def get_whatsapp_config(
    user: CurrentUser = Depends(_ADMIN_ONLY),
    session: Session = Depends(get_session),
) -> WhatsAppConfigResponse:
    cfg = WhatsAppConfigRepository(session).get_for_tenant(user.tenant_id)
    return _to_response(cfg)


@router.put("/whatsapp", response_model=WhatsAppConfigResponse)
def put_whatsapp_config(
    req: WhatsAppConfigUpdateRequest,
    user: CurrentUser = Depends(_ADMIN_ONLY),
    session: Session = Depends(get_session),
) -> WhatsAppConfigResponse:
    repo = WhatsAppConfigRepository(session)
    existing = repo.get_for_tenant(user.tenant_id)

    # access_token semantics:
    #   None      -> keep previous (no change)
    #   ""        -> clear
    #   <string>  -> encrypt + store
    if req.access_token is None:
        token_blob: str | None = None  # signals "keep existing" to repo.upsert
    elif req.access_token == "":
        token_blob = ""  # explicit clear sent as empty ciphertext
    else:
        if not encryption_available():
            raise HTTPException(
                status_code=503,
                detail="Server encryption key not configured; cannot store WhatsApp token",
            )
        try:
            token_blob = encrypt_secret(req.access_token)
        except EncryptionUnavailableError as exc:
            raise HTTPException(status_code=503, detail=str(exc))

    # If the operator wants notifications enabled, they must give us a token
    # AND the row must end up with a token. Refuse otherwise to avoid the UI
    # silently saving a half-configured row.
    if req.enabled:
        existing_token = (
            existing.access_token_encrypted if existing is not None else ""
        ) or ""
        effective_token = token_blob if token_blob is not None else existing_token
        if not effective_token:
            raise HTTPException(
                status_code=400,
                detail="Cannot enable WhatsApp without an access token",
            )
        if not req.phone_number_id:
            raise HTTPException(
                status_code=400,
                detail="Cannot enable WhatsApp without a phone_number_id",
            )
        if not req.template_name:
            raise HTTPException(
                status_code=400,
                detail="Cannot enable WhatsApp without a template_name",
            )
        if not req.recipients:
            raise HTTPException(
                status_code=400,
                detail="Cannot enable WhatsApp without at least one recipient",
            )

    cfg = repo.upsert(
        tenant_id=user.tenant_id,
        enabled=req.enabled,
        phone_number_id=req.phone_number_id,
        access_token_encrypted=token_blob,
        template_name=req.template_name,
        template_language=req.template_language,
        recipients=req.recipients,
        include_image=req.include_image,
    )
    session.commit()
    session.refresh(cfg)
    return _to_response(cfg)


@router.post("/whatsapp/test", response_model=WhatsAppTestResponse)
def test_whatsapp(
    req: WhatsAppTestRequest,
    user: CurrentUser = Depends(_ADMIN_ONLY),
) -> WhatsAppTestResponse:
    # Imported lazily to avoid a circular import: main.py constructs the
    # notifier singleton and exposes it here.
    from app.main import whatsapp_notifier

    result = whatsapp_notifier.send_test(
        tenant_id=user.tenant_id, phone_number=req.phone_number
    )
    return WhatsAppTestResponse(
        ok=bool(result.get("ok")),
        message_id=result.get("message_id"),
        error=result.get("error"),
    )


@router.get("/teams", response_model=TeamsConfigResponse)
def get_teams_config(
    user: CurrentUser = Depends(_ADMIN_ONLY),
    session: Session = Depends(get_session),
) -> TeamsConfigResponse:
    cfg = TeamsConfigRepository(session).get_for_tenant(user.tenant_id)
    return _to_teams_response(cfg)


@router.put("/teams", response_model=TeamsConfigResponse)
def put_teams_config(
    req: TeamsConfigUpdateRequest,
    user: CurrentUser = Depends(_ADMIN_ONLY),
    session: Session = Depends(get_session),
) -> TeamsConfigResponse:
    repo = TeamsConfigRepository(session)
    existing = repo.get_for_tenant(user.tenant_id)

    if req.webhook_url is None:
        webhook_blob: str | None = None
    elif req.webhook_url == "":
        webhook_blob = ""
    else:
        if not encryption_available():
            raise HTTPException(
                status_code=503,
                detail="Server encryption key not configured; cannot store Teams webhook URL",
            )
        try:
            webhook_blob = encrypt_secret(req.webhook_url)
        except EncryptionUnavailableError as exc:
            raise HTTPException(status_code=503, detail=str(exc))

    if req.enabled:
        existing_url = (
            existing.webhook_url_encrypted if existing is not None else ""
        ) or ""
        effective_url = webhook_blob if webhook_blob is not None else existing_url
        if not effective_url:
            raise HTTPException(
                status_code=400,
                detail="Cannot enable Teams without a webhook_url",
            )

    cfg = repo.upsert(
        tenant_id=user.tenant_id,
        enabled=req.enabled,
        webhook_url_encrypted=webhook_blob,
        channel_name=req.channel_name,
        notify_on_confirmed=req.notify_on_confirmed,
    )
    session.commit()
    session.refresh(cfg)
    return _to_teams_response(cfg)


@router.post("/teams/test", response_model=TeamsTestResponse)
def test_teams(
    user: CurrentUser = Depends(_ADMIN_ONLY),
) -> TeamsTestResponse:
    from app.main import teams_notifier

    result = teams_notifier.send_test(tenant_id=user.tenant_id)
    return TeamsTestResponse(
        ok=bool(result.get("ok")),
        status_code=result.get("status_code"),
        error=result.get("error"),
    )
