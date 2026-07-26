"""Notification integration config endpoints.

Per-tenant config + a test-send endpoint reviewers can use to confirm
the provider credentials work before turning notifications on. All endpoints
require role `admin` because stored webhook URLs and tokens are sensitive.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.dependencies import CurrentUser, require_role
from app.config import settings
from app.db.base import get_session
from app.notifications.schemas import (
    TeamsConfigResponse,
    TeamsConfigUpdateRequest,
    TeamsTestResponse,
    WhatsAppConfigResponse,
    WhatsAppConfigUpdateRequest,
    WhatsAppOperatorCreateRequest,
    WhatsAppOperatorOut,
    WhatsAppOperatorUpdateRequest,
    WhatsAppTestRequest,
    WhatsAppTestResponse,
)
from app.repositories import (
    TeamsConfigRepository,
    WhatsAppConfigRepository,
    WhatsAppOperatorRepository,
)
from app.services.crypto import (
    EncryptionUnavailableError,
    encrypt_secret,
    encryption_available,
)

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


_ADMIN_ONLY = require_role("admin")


def _wa_connected() -> bool:
    """True when the platform's shared Meta number is fully configured."""
    return bool(
        settings.WHATSAPP_PHONE_NUMBER_ID
        and settings.WHATSAPP_ACCESS_TOKEN
        and settings.WHATSAPP_TEMPLATE_NAME
    )


def _operator_out(op) -> WhatsAppOperatorOut:  # type: ignore[no-untyped-def]
    return WhatsAppOperatorOut(
        id=str(op.id), phone=op.phone, name=op.name, enabled=op.enabled
    )


def _to_response(cfg, operators) -> WhatsAppConfigResponse:  # type: ignore[no-untyped-def]
    connected = _wa_connected()
    stored_enabled = bool(cfg.enabled) if cfg is not None else False
    return WhatsAppConfigResponse(
        # Effective enabled: a tenant can't be "on" while the platform number is
        # not configured. Avoids a stranded enabled=true the UI can't toggle off.
        enabled=stored_enabled and connected,
        include_image=bool(cfg.include_image) if cfg is not None else True,
        connected=connected,
        operators=[_operator_out(o) for o in operators],
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
    operators = WhatsAppOperatorRepository(session).list_for_tenant(user.tenant_id)
    return _to_response(cfg, operators)


@router.put("/whatsapp", response_model=WhatsAppConfigResponse)
def put_whatsapp_config(
    req: WhatsAppConfigUpdateRequest,
    user: CurrentUser = Depends(_ADMIN_ONLY),
    session: Session = Depends(get_session),
) -> WhatsAppConfigResponse:
    if req.enabled and not _wa_connected():
        raise HTTPException(
            status_code=400,
            detail="Credenciais Meta da plataforma não configuradas no servidor.",
        )
    repo = WhatsAppConfigRepository(session)
    repo.upsert(
        tenant_id=user.tenant_id,
        enabled=req.enabled,
        include_image=req.include_image,
    )
    session.commit()
    cfg = repo.get_for_tenant(user.tenant_id)
    operators = WhatsAppOperatorRepository(session).list_for_tenant(user.tenant_id)
    return _to_response(cfg, operators)


@router.post("/whatsapp/operators", response_model=WhatsAppOperatorOut, status_code=201)
def add_whatsapp_operator(
    req: WhatsAppOperatorCreateRequest,
    user: CurrentUser = Depends(_ADMIN_ONLY),
    session: Session = Depends(get_session),
) -> WhatsAppOperatorOut:
    repo = WhatsAppOperatorRepository(session)
    try:
        op = repo.add(user.tenant_id, phone=req.phone, name=req.name)
        session.commit()
    except IntegrityError:
        # `phone` is globally unique — an operator belongs to exactly one tenant.
        session.rollback()
        raise HTTPException(
            status_code=409,
            detail="Este número já está vinculado a outro tenant.",
        )
    session.refresh(op)
    return _operator_out(op)


@router.patch(
    "/whatsapp/operators/{operator_id}", response_model=WhatsAppOperatorOut
)
def update_whatsapp_operator(
    operator_id: str,
    req: WhatsAppOperatorUpdateRequest,
    user: CurrentUser = Depends(_ADMIN_ONLY),
    session: Session = Depends(get_session),
) -> WhatsAppOperatorOut:
    repo = WhatsAppOperatorRepository(session)
    op = repo.update(
        user.tenant_id, operator_id, enabled=req.enabled, name=req.name
    )
    if op is None:
        raise HTTPException(status_code=404, detail="Operador não encontrado.")
    session.commit()
    session.refresh(op)
    return _operator_out(op)


@router.delete("/whatsapp/operators/{operator_id}", status_code=204)
def delete_whatsapp_operator(
    operator_id: str,
    user: CurrentUser = Depends(_ADMIN_ONLY),
    session: Session = Depends(get_session),
) -> None:
    repo = WhatsAppOperatorRepository(session)
    if not repo.remove(user.tenant_id, operator_id):
        raise HTTPException(status_code=404, detail="Operador não encontrado.")
    session.commit()


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
