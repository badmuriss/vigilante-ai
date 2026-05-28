"""Send confirmed-alert notifications to Microsoft Teams Workflows webhooks."""

from __future__ import annotations

import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Sequence

import httpx
from sqlalchemy import select

from app.config import settings
from app.db.base import session_scope
from app.db.entities import Alert, Camera, Site, TeamsConfig
from app.observability import teams_messages_total
from app.services.crypto import SecretDecryptError, decrypt_secret, encryption_available

logger = logging.getLogger(__name__)

_EPI_LABELS_PT: dict[str, str] = {
    "capacete": "Capacete",
    "colete": "Colete refletivo",
    "oculos": "Oculos de protecao",
    "luvas": "Luvas",
    "mascara": "Mascara",
    "botas": "Botas",
}


@dataclass(frozen=True)
class _AlertSnapshot:
    id: str
    camera_id: str
    violation_type: str
    missing_epis: list[str]
    confidence: float
    timestamp: datetime


@dataclass(frozen=True)
class _TenantContext:
    tenant_id: str
    camera_name: str
    site_name: str
    site_location: str | None


def _snapshot(alert: Alert) -> _AlertSnapshot:
    return _AlertSnapshot(
        id=str(alert.id),
        camera_id=str(alert.camera_id),
        violation_type=alert.violation_type,
        missing_epis=list(alert.missing_epis or []),
        confidence=float(alert.confidence or 0.0),
        timestamp=alert.timestamp,
    )


def _format_epis(missing: Sequence[str]) -> str:
    if not missing:
        return "EPI nao identificado"
    return ", ".join(_EPI_LABELS_PT.get(k, k) for k in missing)


def _format_timestamp(ts: datetime) -> str:
    return ts.strftime("%d/%m/%Y %H:%M")


def _truncate(value: str, max_len: int = 256) -> str:
    if len(value) <= max_len:
        return value
    return value[: max_len - 1] + "..."


class TeamsNotifier:
    """Dispatch alert notifications to Microsoft Teams asynchronously."""

    def __init__(
        self,
        *,
        http_client: httpx.Client | None = None,
        max_workers: int | None = None,
    ) -> None:
        self._owned_client = http_client is None
        self._client = http_client or httpx.Client(timeout=settings.TEAMS_HTTP_TIMEOUT)
        self._executor = ThreadPoolExecutor(
            max_workers=max_workers or settings.TEAMS_DISPATCH_WORKERS,
            thread_name_prefix="teams-notifier",
        )
        self._lock = threading.Lock()
        self._closed = False

    def notify_async(self, alert: Alert) -> None:
        try:
            snap = _snapshot(alert)
        except Exception:
            logger.exception("Failed to snapshot alert for Teams dispatch")
            return
        with self._lock:
            if self._closed:
                logger.warning("Teams notifier closed; dropping alert %s", snap.id)
                return
            try:
                self._executor.submit(self._send_job, snap)
            except RuntimeError:
                logger.warning("Teams executor refused job for alert %s", snap.id)

    def send_test(self, *, tenant_id: str) -> dict[str, Any]:
        config = self._load_config(tenant_id)
        if config is None:
            return {"ok": False, "error": "Teams config not found for this tenant"}
        validation = self._validate_config(config)
        if validation is not None:
            return {"ok": False, "error": validation}
        url = self._decrypt_url(config, tenant_id)
        if url is None:
            return {"ok": False, "error": "could not decrypt Teams webhook URL"}
        payload = self._build_card_payload(
            title="Teste de configuracao",
            subtitle="Vigilante.AI conseguiu enviar uma mensagem para o Teams.",
            facts=[
                ("Origem", "Vigilante.AI"),
                ("Canal", config.channel_name or "Nao informado"),
                ("Horario", _format_timestamp(datetime.now(timezone.utc))),
            ],
            alert_url=None,
        )
        return self._post(url, payload)

    def shutdown(self, wait: bool = True) -> None:
        with self._lock:
            self._closed = True
        self._executor.shutdown(wait=wait)
        if self._owned_client:
            self._client.close()

    def _send_job(self, snap: _AlertSnapshot) -> None:
        try:
            self._dispatch(snap)
        except Exception:
            logger.exception("Teams dispatch crashed for alert %s", snap.id)

    def _dispatch(self, snap: _AlertSnapshot) -> None:
        ctx = self._load_tenant_context(snap.camera_id)
        if ctx is None:
            logger.warning("No tenant context for camera %s", snap.camera_id)
            return
        config = self._load_config(ctx.tenant_id)
        if config is None or not config.enabled or not config.notify_on_confirmed:
            teams_messages_total.labels(
                tenant_id=ctx.tenant_id, outcome="skipped"
            ).inc()
            return
        validation = self._validate_config(config)
        if validation is not None:
            logger.info(
                "Teams config invalid for tenant %s: %s", ctx.tenant_id, validation
            )
            teams_messages_total.labels(
                tenant_id=ctx.tenant_id, outcome="skipped"
            ).inc()
            return
        url = self._decrypt_url(config, ctx.tenant_id)
        if url is None:
            teams_messages_total.labels(
                tenant_id=ctx.tenant_id, outcome="failed"
            ).inc()
            return

        facts = [
            ("Camera", ctx.camera_name),
            ("Local", ctx.site_location or ctx.site_name),
            ("EPIs faltantes", _format_epis(snap.missing_epis)),
            ("Confianca", f"{round(snap.confidence * 100)}%"),
            ("Horario", _format_timestamp(snap.timestamp)),
        ]
        result = self._post(
            url,
            self._build_card_payload(
                title="Alerta de seguranca confirmado",
                subtitle=snap.violation_type.replace("_", " "),
                facts=facts,
                alert_url=self._alert_url(snap.id),
            ),
        )
        outcome = "sent" if result.get("ok") else "failed"
        teams_messages_total.labels(tenant_id=ctx.tenant_id, outcome=outcome).inc()
        if not result.get("ok"):
            logger.warning(
                "Teams send failed alert=%s error=%s",
                snap.id,
                result.get("error"),
            )

    def _decrypt_url(self, config: TeamsConfig, tenant_id: str) -> str | None:
        if not encryption_available():
            logger.error("Cannot decrypt Teams webhook URL: encryption key not configured")
            return None
        try:
            return decrypt_secret(config.webhook_url_encrypted or "")
        except SecretDecryptError:
            logger.exception("Failed to decrypt Teams webhook URL for tenant %s", tenant_id)
            return None

    def _post(self, webhook_url: str, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            resp = self._client.post(
                webhook_url,
                headers={"Content-Type": "application/json"},
                json=payload,
            )
        except httpx.HTTPError as exc:
            return {"ok": False, "error": f"network: {exc}"}
        body = resp.text[:500]
        if resp.status_code >= 400:
            return {
                "ok": False,
                "status_code": resp.status_code,
                "error": f"HTTP {resp.status_code}: {body}",
            }
        if (
            "Microsoft Teams endpoint returned HTTP error" in body
            or "Webhook message delivery failed" in body
        ):
            return {
                "ok": False,
                "status_code": resp.status_code,
                "error": body,
            }
        return {"ok": True, "status_code": resp.status_code}

    @staticmethod
    def _build_card_payload(
        *,
        title: str,
        subtitle: str,
        facts: Sequence[tuple[str, str]],
        alert_url: str | None,
    ) -> dict[str, Any]:
        content: dict[str, Any] = {
            "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
            "type": "AdaptiveCard",
            "version": "1.2",
            "body": [
                {
                    "type": "TextBlock",
                    "text": title,
                    "weight": "Bolder",
                    "size": "Medium",
                    "color": "Attention",
                    "wrap": True,
                },
                {
                    "type": "TextBlock",
                    "text": _truncate(subtitle),
                    "wrap": True,
                    "spacing": "Small",
                },
                {
                    "type": "FactSet",
                    "facts": [
                        {
                            "title": f"{_truncate(label, 40)}:",
                            "value": _truncate(value),
                        }
                        for label, value in facts
                    ],
                },
            ],
        }
        if alert_url:
            content["actions"] = [
                {
                    "type": "Action.OpenUrl",
                    "title": "Abrir no Vigilante.AI",
                    "url": alert_url,
                }
            ]
        return {
            "type": "message",
            "attachments": [
                {
                    "contentType": "application/vnd.microsoft.card.adaptive",
                    "contentUrl": None,
                    "content": content,
                }
            ],
        }

    @staticmethod
    def _alert_url(alert_id: str) -> str | None:
        base = settings.PUBLIC_APP_URL.strip().rstrip("/")
        if not base:
            return None
        return f"{base}/historico?alert={alert_id}"

    @staticmethod
    def _load_tenant_context(camera_id: str) -> _TenantContext | None:
        with session_scope() as session:
            row = session.execute(
                select(Camera, Site).join(Site, Site.id == Camera.site_id).where(
                    Camera.id == camera_id
                )
            ).first()
            if row is None:
                return None
            camera, site = row
            return _TenantContext(
                tenant_id=str(site.tenant_id),
                camera_name=camera.name,
                site_name=site.name,
                site_location=site.location,
            )

    @staticmethod
    def _load_config(tenant_id: str) -> TeamsConfig | None:
        with session_scope() as session:
            cfg = session.scalar(
                select(TeamsConfig).where(TeamsConfig.tenant_id == tenant_id)
            )
            if cfg is not None:
                session.expunge(cfg)
            return cfg

    @staticmethod
    def _validate_config(config: TeamsConfig) -> str | None:
        if not config.webhook_url_encrypted:
            return "webhook_url is empty"
        return None
