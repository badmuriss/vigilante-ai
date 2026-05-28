"""Send confirmed-alert notifications via the Meta WhatsApp Cloud API.

Plugged into `POST /api/alerts/{id}/feedback` after the feedback commit:
when a reviewer marks an alert as `correct`, `notify_async` enqueues a
job onto a daemon thread pool that:

1. Resolves the alert's tenant and loads its `WhatsAppConfig`.
2. If `include_image=True`, uploads the alert's annotated frame to
   `/{phone_number_id}/media` once, reusing the returned `media_id` for
   every recipient.
3. For each recipient, sends a template message
   (`POST /{phone_number_id}/messages`) with header image (optional) and
   body parameters {camera, EPI list, timestamp}.

Design notes:
- Worker thread isolation: the FastAPI request thread is never blocked
  by Meta's HTTP latency; failures stay confined to the worker and only
  surface in logs + Prometheus counter `vigilante_whatsapp_messages_total`.
- Template-only: Meta requires a pre-approved template for
  business-initiated messages outside the 24-hour customer window.
  Template name + language are tenant-configurable.
- Pure stdlib snapshot: the alert is read on the request thread (where
  the SQLA session is alive) and passed to the worker as a plain
  `_AlertSnapshot` so the worker never touches detached ORM state.
"""

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
from app.db.entities import Alert, Camera, Site, WhatsAppConfig
from app.observability import whatsapp_messages_total
from app.services.crypto import (
    SecretDecryptError,
    decrypt_secret,
    encryption_available,
)
from app.storage import BlobStore

logger = logging.getLogger(__name__)


# Friendly PT-BR labels for the EPI keys carried on the Alert payload.
# Mirrors `app.detector.EPI_LABELS_PT` but kept local to avoid pulling
# the heavy detector module into the notifier just for labels.
_EPI_LABELS_PT: dict[str, str] = {
    "capacete": "Capacete",
    "colete": "Colete refletivo",
    "oculos": "Óculos de proteção",
    "luvas": "Luvas",
    "mascara": "Máscara",
    "botas": "Botas",
}


@dataclass(frozen=True)
class _AlertSnapshot:
    """Plain-data view of an Alert, safe to hand off to a worker thread."""

    id: str
    camera_id: str
    violation_type: str
    missing_epis: list[str]
    timestamp: datetime
    frame_path: str | None


def _snapshot(alert: Alert) -> _AlertSnapshot:
    return _AlertSnapshot(
        id=str(alert.id),
        camera_id=str(alert.camera_id),
        violation_type=alert.violation_type,
        missing_epis=list(alert.missing_epis or []),
        timestamp=alert.timestamp,
        frame_path=alert.frame_path,
    )


@dataclass(frozen=True)
class _TenantContext:
    tenant_id: str
    camera_name: str
    site_location: str | None


def _format_epis(missing: Sequence[str]) -> str:
    if not missing:
        return "EPI não identificado"
    return ", ".join(_EPI_LABELS_PT.get(k, k) for k in missing)


def _format_timestamp(ts: datetime) -> str:
    # WhatsApp template parameters cannot contain newlines or 4+ spaces.
    return ts.strftime("%d/%m/%Y %H:%M")


def _to_meta_recipient(value: str) -> str:
    """Convert stored E.164 values to Meta's numeric recipient format."""
    return value[1:] if value.startswith("+") else value


class WhatsAppNotifier:
    """Dispatch alert notifications to WhatsApp asynchronously.

    A single executor is reused across requests. `shutdown()` should be
    called on app teardown to drain in-flight jobs gracefully.
    """

    def __init__(
        self,
        blob_store: BlobStore,
        *,
        http_client: httpx.Client | None = None,
        max_workers: int | None = None,
    ) -> None:
        self._blob_store = blob_store
        self._owned_client = http_client is None
        self._client = http_client or httpx.Client(
            timeout=settings.WHATSAPP_HTTP_TIMEOUT,
            base_url=settings.WHATSAPP_API_BASE,
        )
        self._executor = ThreadPoolExecutor(
            max_workers=max_workers or settings.WHATSAPP_DISPATCH_WORKERS,
            thread_name_prefix="wa-notifier",
        )
        self._lock = threading.Lock()
        self._closed = False

    # --- public API ---

    def notify_async(self, alert: Alert) -> None:
        """Snapshot the alert and dispatch the send to the worker pool.

        Safe to call inside a request handler — never blocks on network.
        Errors during dispatch (e.g. executor shut down) are logged but
        never raised to the caller.
        """
        try:
            snap = _snapshot(alert)
        except Exception:
            logger.exception("Failed to snapshot alert for WhatsApp dispatch")
            return
        with self._lock:
            if self._closed:
                logger.warning("Notifier closed; dropping alert %s", snap.id)
                return
            try:
                self._executor.submit(self._send_job, snap)
            except RuntimeError:
                logger.warning("Executor refused job for alert %s", snap.id)

    def send_test(
        self,
        *,
        tenant_id: str,
        phone_number: str,
    ) -> dict[str, Any]:
        """Synchronously send a no-image test message to one recipient.

        Returns a dict with `ok` and either `message_id` or `error`. Used
        by the configuration UI to validate setup. Runs on the request
        thread by design — the operator wants the error inline.
        """
        config = self._load_config(tenant_id)
        if config is None:
            return {"ok": False, "error": "WhatsApp config not found for this tenant"}
        validation = self._validate_config(config, require_recipients=False)
        if validation is not None:
            return {"ok": False, "error": validation}
        try:
            token = decrypt_secret(config.access_token_encrypted or "")
        except SecretDecryptError as exc:
            return {"ok": False, "error": str(exc)}
        try:
            result = self._send_text(
                phone_number_id=config.phone_number_id or "",
                token=token,
                to=phone_number,
                template_name=config.template_name or "",
                language=config.template_language or "pt_BR",
                body_params=[
                    "Teste de configuração",
                    "Vigilante.AI",
                    _format_timestamp(datetime.now(timezone.utc)),
                ],
                media_id=None,
            )
        except httpx.HTTPError as exc:
            return {"ok": False, "error": f"Network error: {exc}"}
        return result

    def shutdown(self, wait: bool = True) -> None:
        with self._lock:
            self._closed = True
        self._executor.shutdown(wait=wait)
        if self._owned_client:
            self._client.close()

    # --- worker ---

    def _send_job(self, snap: _AlertSnapshot) -> None:
        try:
            self._dispatch(snap)
        except Exception:
            logger.exception("WhatsApp dispatch crashed for alert %s", snap.id)

    def _dispatch(self, snap: _AlertSnapshot) -> None:
        ctx = self._load_tenant_context(snap.camera_id)
        if ctx is None:
            logger.warning("No tenant context for camera %s", snap.camera_id)
            return
        config = self._load_config(ctx.tenant_id)
        if config is None or not config.enabled:
            whatsapp_messages_total.labels(
                tenant_id=ctx.tenant_id, outcome="skipped"
            ).inc()
            return
        validation = self._validate_config(config)
        if validation is not None:
            logger.info(
                "WhatsApp config invalid for tenant %s: %s", ctx.tenant_id, validation
            )
            whatsapp_messages_total.labels(
                tenant_id=ctx.tenant_id, outcome="skipped"
            ).inc()
            return
        if not encryption_available():
            logger.error("Cannot decrypt WhatsApp token: encryption key not configured")
            whatsapp_messages_total.labels(
                tenant_id=ctx.tenant_id, outcome="failed"
            ).inc()
            return
        try:
            token = decrypt_secret(config.access_token_encrypted or "")
        except SecretDecryptError:
            logger.exception("Failed to decrypt WhatsApp token for tenant %s", ctx.tenant_id)
            whatsapp_messages_total.labels(
                tenant_id=ctx.tenant_id, outcome="failed"
            ).inc()
            return

        media_id: str | None = None
        if config.include_image and snap.frame_path:
            media_id = self._upload_media(
                phone_number_id=config.phone_number_id or "",
                token=token,
                frame_path=snap.frame_path,
                alert_id=snap.id,
            )

        body_params = [
            ctx.camera_name,
            _format_epis(snap.missing_epis),
            _format_timestamp(snap.timestamp),
        ]
        for recipient in config.recipients or []:
            result = self._send_text(
                phone_number_id=config.phone_number_id or "",
                token=token,
                to=recipient,
                template_name=config.template_name or "",
                language=config.template_language or "pt_BR",
                body_params=body_params,
                media_id=media_id,
            )
            outcome = "sent" if result.get("ok") else "failed"
            whatsapp_messages_total.labels(
                tenant_id=ctx.tenant_id, outcome=outcome
            ).inc()
            if not result.get("ok"):
                logger.warning(
                    "WhatsApp send failed alert=%s recipient=%s error=%s",
                    snap.id,
                    recipient,
                    result.get("error"),
                )

    # --- HTTP layer ---

    def _upload_media(
        self,
        *,
        phone_number_id: str,
        token: str,
        frame_path: str,
        alert_id: str,
    ) -> str | None:
        data = self._blob_store.load_bytes(frame_path)
        if not data:
            logger.info("Alert %s frame missing on disk; sending text-only", alert_id)
            return None
        try:
            resp = self._client.post(
                f"/{phone_number_id}/media",
                headers={"Authorization": f"Bearer {token}"},
                data={"messaging_product": "whatsapp", "type": "image/jpeg"},
                files={"file": (f"{alert_id}.jpg", data, "image/jpeg")},
            )
        except httpx.HTTPError:
            logger.exception("WhatsApp media upload failed for alert %s", alert_id)
            return None
        if resp.status_code >= 400:
            logger.warning(
                "WhatsApp media upload non-2xx alert=%s status=%s body=%s",
                alert_id,
                resp.status_code,
                resp.text[:500],
            )
            return None
        try:
            return str(resp.json().get("id"))
        except ValueError:
            logger.warning("WhatsApp media upload returned non-JSON body")
            return None

    def _send_text(
        self,
        *,
        phone_number_id: str,
        token: str,
        to: str,
        template_name: str,
        language: str,
        body_params: Sequence[str],
        media_id: str | None,
    ) -> dict[str, Any]:
        components: list[dict[str, Any]] = []
        if media_id:
            components.append(
                {
                    "type": "header",
                    "parameters": [
                        {"type": "image", "image": {"id": media_id}},
                    ],
                }
            )
        components.append(
            {
                "type": "body",
                "parameters": [
                    {"type": "text", "text": str(p)} for p in body_params
                ],
            }
        )
        payload: dict[str, Any] = {
            "messaging_product": "whatsapp",
            "to": _to_meta_recipient(to),
            "type": "template",
            "template": {
                "name": template_name,
                "language": {"code": language},
                "components": components,
            },
        }
        try:
            resp = self._client.post(
                f"/{phone_number_id}/messages",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
        except httpx.HTTPError as exc:
            return {"ok": False, "error": f"network: {exc}"}
        if resp.status_code >= 400:
            return {
                "ok": False,
                "error": f"HTTP {resp.status_code}: {resp.text[:500]}",
            }
        try:
            body = resp.json()
        except ValueError:
            return {"ok": False, "error": "non-JSON response from Meta"}
        messages = body.get("messages") or []
        if not messages:
            return {"ok": False, "error": f"unexpected response: {body}"}
        return {"ok": True, "message_id": messages[0].get("id")}

    # --- DB lookups (own session per call to stay thread-safe) ---

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
                site_location=site.location,
            )

    @staticmethod
    def _load_config(tenant_id: str) -> WhatsAppConfig | None:
        with session_scope() as session:
            cfg = session.scalar(
                select(WhatsAppConfig).where(WhatsAppConfig.tenant_id == tenant_id)
            )
            if cfg is not None:
                session.expunge(cfg)
            return cfg

    @staticmethod
    def _validate_config(
        config: WhatsAppConfig, *, require_recipients: bool = True
    ) -> str | None:
        """Return a human-readable reason if the config is not sendable."""
        if not config.phone_number_id:
            return "phone_number_id is empty"
        if not config.access_token_encrypted:
            return "access token not set"
        if not config.template_name:
            return "template_name is empty"
        if require_recipients and not config.recipients:
            return "no recipients configured"
        return None


# --- Inbound conversational replies (free-form, used by the chat webhook) ---
#
# Within the 24h customer-service window (opened when the user messages us),
# Meta allows free-form `type: "text"` replies — no pre-approved template
# needed. The chat webhook uses these to answer inbound questions.


def _load_config_by_id(config_id: str) -> WhatsAppConfig | None:
    with session_scope() as session:
        cfg = session.scalar(
            select(WhatsAppConfig).where(WhatsAppConfig.id == config_id)
        )
        if cfg is not None:
            session.expunge(cfg)
        return cfg


def send_session_text(config_id: str, *, to: str, body: str) -> dict[str, Any]:
    """Send a free-form WhatsApp text reply. Returns {ok, message_id|error}."""
    cfg = _load_config_by_id(config_id)
    if cfg is None:
        return {"ok": False, "error": "config not found"}
    if not cfg.phone_number_id or not cfg.access_token_encrypted:
        return {"ok": False, "error": "incomplete WhatsApp config"}
    if not encryption_available():
        return {"ok": False, "error": "encryption key not configured"}
    try:
        token = decrypt_secret(cfg.access_token_encrypted)
    except SecretDecryptError as exc:
        return {"ok": False, "error": str(exc)}

    payload = {
        "messaging_product": "whatsapp",
        "to": _to_meta_recipient(to),
        "type": "text",
        "text": {"body": body},
    }
    try:
        with httpx.Client(
            timeout=settings.WHATSAPP_HTTP_TIMEOUT, base_url=settings.WHATSAPP_API_BASE
        ) as client:
            resp = client.post(
                f"/{cfg.phone_number_id}/messages",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
    except httpx.HTTPError as exc:
        return {"ok": False, "error": f"network: {exc}"}
    if resp.status_code >= 400:
        return {"ok": False, "error": f"HTTP {resp.status_code}: {resp.text[:500]}"}
    try:
        messages = resp.json().get("messages") or []
    except ValueError:
        return {"ok": False, "error": "non-JSON response"}
    if not messages:
        return {"ok": False, "error": "no message id returned"}
    return {"ok": True, "message_id": messages[0].get("id")}


def download_media(media_id: str, config_id: str) -> bytes | None:
    """Download inbound media bytes (e.g. a voice note) by Meta media id."""
    cfg = _load_config_by_id(config_id)
    if cfg is None or not cfg.access_token_encrypted or not encryption_available():
        return None
    try:
        token = decrypt_secret(cfg.access_token_encrypted)
    except SecretDecryptError:
        return None
    headers = {"Authorization": f"Bearer {token}"}
    try:
        with httpx.Client(
            timeout=settings.WHATSAPP_HTTP_TIMEOUT, base_url=settings.WHATSAPP_API_BASE
        ) as client:
            meta = client.get(f"/{media_id}", headers=headers)
            if meta.status_code >= 400:
                return None
            url = meta.json().get("url")
            if not url:
                return None
            # The media URL is on a lookaside host; fetch with the same token.
            blob = client.get(url, headers=headers)
            if blob.status_code >= 400:
                return None
            return blob.content
    except httpx.HTTPError:
        logger.exception("WhatsApp media download failed for %s", media_id)
        return None


def is_e164(value: str) -> bool:
    """Light E.164 validation: leading '+', country code 1-9, 7-15 digits total."""
    if not value or not value.startswith("+"):
        return False
    digits = value[1:]
    if not digits.isdigit():
        return False
    if not (7 <= len(digits) <= 15):
        return False
    if digits[0] == "0":
        return False
    return True
