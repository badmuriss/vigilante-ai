"""Unit tests for the Microsoft Teams notifier service."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Iterator

import httpx
import pytest
from cryptography.fernet import Fernet
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app import db
from app.config import settings
from app.db.base import Base
from app.db.entities import Camera, Site, TeamsConfig, Tenant
from app.services import crypto
from app.services.teams_notifier import TeamsNotifier


@pytest.fixture()
def fernet_key(monkeypatch: pytest.MonkeyPatch) -> str:
    key = Fernet.generate_key().decode()
    monkeypatch.setattr(settings, "NOTIFY_ENCRYPTION_KEY", key)
    crypto._fernet.cache_clear()
    return key


@pytest.fixture()
def test_db(monkeypatch: pytest.MonkeyPatch) -> Iterator[sessionmaker[Session]]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        future=True,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False, future=True)

    monkeypatch.setattr(db.base, "_engine", engine, raising=False)
    monkeypatch.setattr(db.base, "_session_factory", factory, raising=False)
    monkeypatch.setattr(db.base, "get_engine", lambda: engine)
    monkeypatch.setattr(db.base, "get_session_factory", lambda: factory)
    monkeypatch.setattr(db.base, "session_scope", lambda: factory())

    from app.services import teams_notifier as tn

    monkeypatch.setattr(tn, "session_scope", lambda: factory())

    yield factory
    engine.dispose()


@pytest.fixture()
def seeded_tenant(
    test_db: sessionmaker[Session], fernet_key: str
) -> tuple[str, str]:
    with test_db() as session:
        tenant = Tenant(name="ACME")
        session.add(tenant)
        session.flush()
        site = Site(tenant_id=tenant.id, name="Obra 1", location="Portao Norte")
        session.add(site)
        session.flush()
        camera = Camera(
            site_id=site.id,
            name="Camera Entrada",
            source_kind="rtsp",
            rtsp_url="rtsp://test",
        )
        session.add(camera)
        session.flush()
        cfg = TeamsConfig(
            tenant_id=tenant.id,
            enabled=True,
            webhook_url_encrypted=crypto.encrypt_secret(
                "https://example.webhook.office.com/workflows/abc"
            ),
            channel_name="Seguranca",
            notify_on_confirmed=True,
        )
        session.add(cfg)
        session.commit()
        return str(tenant.id), str(camera.id)


def _make_alert_snapshot(camera_id: str):
    from app.services.teams_notifier import _AlertSnapshot

    return _AlertSnapshot(
        id="alert-123",
        camera_id=camera_id,
        violation_type="capacete_ausente",
        missing_epis=["capacete"],
        confidence=0.94,
        timestamp=datetime(2026, 5, 25, 14, 30),
    )


def test_send_test_posts_adaptive_card(seeded_tenant: tuple[str, str]) -> None:
    tenant_id, _camera_id = seeded_tenant
    requests: list[httpx.Request] = []

    def handler(req: httpx.Request) -> httpx.Response:
        requests.append(req)
        return httpx.Response(200, text="1")

    notifier = TeamsNotifier(
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
        max_workers=1,
    )
    result = notifier.send_test(tenant_id=tenant_id)
    notifier.shutdown(wait=False)

    assert result == {"ok": True, "status_code": 200}
    assert len(requests) == 1
    payload = json.loads(requests[0].content)
    assert payload["type"] == "message"
    attachment = payload["attachments"][0]
    assert attachment["contentType"] == "application/vnd.microsoft.card.adaptive"
    assert attachment["content"]["type"] == "AdaptiveCard"


def test_dispatch_confirmed_alert_posts_incident_card(
    seeded_tenant: tuple[str, str],
) -> None:
    _tenant_id, camera_id = seeded_tenant
    requests: list[httpx.Request] = []

    def handler(req: httpx.Request) -> httpx.Response:
        requests.append(req)
        return httpx.Response(200, text="1")

    notifier = TeamsNotifier(
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
        max_workers=1,
    )
    notifier._dispatch(_make_alert_snapshot(camera_id))
    notifier.shutdown(wait=False)

    assert len(requests) == 1
    payload = json.loads(requests[0].content)
    card = payload["attachments"][0]["content"]
    assert card["body"][0]["text"] == "Alerta de seguranca confirmado"
    facts = card["body"][2]["facts"]
    assert {"title": "Camera:", "value": "Camera Entrada"} in facts
    assert {"title": "EPIs faltantes:", "value": "Capacete"} in facts
    assert {"title": "Confianca:", "value": "94%"} in facts


def test_dispatch_skips_when_disabled(
    seeded_tenant: tuple[str, str],
    test_db: sessionmaker[Session],
) -> None:
    _tenant_id, camera_id = seeded_tenant
    with test_db() as session:
        cfg = session.query(TeamsConfig).first()
        assert cfg is not None
        cfg.enabled = False
        session.commit()

    requests: list[httpx.Request] = []

    def handler(req: httpx.Request) -> httpx.Response:
        requests.append(req)
        return httpx.Response(200, text="1")

    notifier = TeamsNotifier(
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
        max_workers=1,
    )
    notifier._dispatch(_make_alert_snapshot(camera_id))
    notifier.shutdown(wait=False)

    assert requests == []


def test_post_treats_teams_error_body_as_failure(
    seeded_tenant: tuple[str, str],
) -> None:
    tenant_id, _camera_id = seeded_tenant

    def handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            text="Microsoft Teams endpoint returned HTTP error 429",
        )

    notifier = TeamsNotifier(
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
        max_workers=1,
    )
    result = notifier.send_test(tenant_id=tenant_id)
    notifier.shutdown(wait=False)

    assert result["ok"] is False
    assert "429" in (result.get("error") or "")


def test_notify_async_does_not_raise_when_executor_closed(
    seeded_tenant: tuple[str, str],
) -> None:
    _tenant_id, camera_id = seeded_tenant

    def handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="1")

    notifier = TeamsNotifier(
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
        max_workers=1,
    )
    notifier.shutdown(wait=True)

    fake_alert = type(
        "_Alert",
        (),
        {
            "id": "alert-123",
            "camera_id": camera_id,
            "violation_type": "x",
            "missing_epis": [],
            "confidence": 1.0,
            "timestamp": datetime(2026, 5, 25, 0, 0),
        },
    )()

    notifier.notify_async(fake_alert)  # type: ignore[arg-type]
