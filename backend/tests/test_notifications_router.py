"""Tests for the WhatsApp notifications config router.

Focus: CRUD shape, role enforcement, token redaction, validation rules
for enable. Sidesteps the heavy app.main import by mounting the router
onto a minimal FastAPI app and overriding dependencies.
"""

from __future__ import annotations

from typing import Iterator

import pytest
from cryptography.fernet import Fernet
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app import db
from app.auth.dependencies import CurrentUser
from app.config import settings
from app.db.base import Base, get_session
from app.db.entities import Tenant, WhatsAppOperator
from app.notifications.router import router as notifications_router
from app.services import crypto


TEST_TENANT_ID = "00000000-0000-0000-0000-000000000001"
OTHER_TENANT_ID = "00000000-0000-0000-0000-000000000002"


def _make_user(role: str) -> CurrentUser:
    return CurrentUser(
        id="00000000-0000-0000-0000-000000000099",
        email="op@test",
        role=role,
        tenant_id=TEST_TENANT_ID,
    )


@pytest.fixture()
def fernet_key(monkeypatch: pytest.MonkeyPatch) -> str:
    key = Fernet.generate_key().decode()
    monkeypatch.setattr(settings, "NOTIFY_ENCRYPTION_KEY", key)
    crypto._fernet.cache_clear()
    return key


@pytest.fixture()
def wa_connected(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make the platform's shared Meta number look configured (env)."""
    monkeypatch.setattr(settings, "WHATSAPP_PHONE_NUMBER_ID", "111222333")
    monkeypatch.setattr(settings, "WHATSAPP_ACCESS_TOKEN", "META_TOKEN")
    monkeypatch.setattr(settings, "WHATSAPP_TEMPLATE_NAME", "safety_alert_pt")


@pytest.fixture()
def test_db(monkeypatch: pytest.MonkeyPatch) -> Iterator[sessionmaker[Session]]:
    # StaticPool: TestClient dispatches handlers to a worker thread, and
    # SQLite's default SingletonThreadPool opens a fresh :memory: per thread
    # — using StaticPool keeps the single shared in-memory DB across threads.
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        future=True,
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False, future=True)
    monkeypatch.setattr(db.base, "_engine", engine, raising=False)
    monkeypatch.setattr(db.base, "_session_factory", factory, raising=False)
    monkeypatch.setattr(db.base, "get_session_factory", lambda: factory)
    # Seed a tenant whose id matches the CurrentUser stub in _make_user.
    with factory() as session:
        session.add(Tenant(id=TEST_TENANT_ID, name="ACME"))
        session.commit()
    yield factory
    engine.dispose()


@pytest.fixture()
def client_admin(
    test_db: sessionmaker[Session], fernet_key: str
) -> Iterator[TestClient]:
    app = FastAPI()
    app.include_router(notifications_router)

    def _session_override() -> Iterator[Session]:
        with test_db() as s:
            yield s

    app.dependency_overrides[get_session] = _session_override

    # Override the admin-only dep — the router imports a closure object
    # assigned to module-level `_ADMIN_ONLY`, so we patch that.
    from app.notifications import router as router_module

    app.dependency_overrides[router_module._ADMIN_ONLY] = lambda: _make_user("admin")

    with TestClient(app) as c:
        yield c


@pytest.fixture()
def client_viewer(
    test_db: sessionmaker[Session], fernet_key: str
) -> Iterator[TestClient]:
    app = FastAPI()
    app.include_router(notifications_router)

    def _session_override() -> Iterator[Session]:
        with test_db() as s:
            yield s

    app.dependency_overrides[get_session] = _session_override

    # Simulate a viewer hitting the admin gate by raising the real 403.
    from app.notifications import router as router_module
    from fastapi import HTTPException

    def _viewer_blocked() -> CurrentUser:
        raise HTTPException(status_code=403, detail="Insufficient role")

    app.dependency_overrides[router_module._ADMIN_ONLY] = _viewer_blocked

    with TestClient(app) as c:
        yield c


# ---------- tests ----------


def test_get_returns_disabled_defaults_when_no_config(client_admin: TestClient) -> None:
    res = client_admin.get("/api/notifications/whatsapp")
    assert res.status_code == 200
    body = res.json()
    assert body["enabled"] is False
    assert body["include_image"] is True
    assert body["operators"] == []
    assert "connected" in body

    teams_res = client_admin.get("/api/notifications/teams")
    assert teams_res.status_code == 200
    teams_body = teams_res.json()
    assert teams_body["enabled"] is False
    assert teams_body["has_webhook_url"] is False
    assert teams_body["notify_on_confirmed"] is True


def test_put_config_round_trip(
    client_admin: TestClient, wa_connected: None
) -> None:
    res = client_admin.put(
        "/api/notifications/whatsapp",
        json={"enabled": True, "include_image": False},
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["enabled"] is True
    assert body["include_image"] is False
    assert body["connected"] is True

    res2 = client_admin.get("/api/notifications/whatsapp")
    assert res2.status_code == 200
    assert res2.json()["enabled"] is True
    assert res2.json()["include_image"] is False


def test_enabled_reported_false_when_creds_lost(
    client_admin: TestClient, wa_connected: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    client_admin.put(
        "/api/notifications/whatsapp",
        json={"enabled": True, "include_image": True},
    )
    # Platform loses its credentials -> effective enabled must read False so the
    # UI never strands a checked+disabled switch.
    monkeypatch.setattr(settings, "WHATSAPP_PHONE_NUMBER_ID", "")
    monkeypatch.setattr(settings, "WHATSAPP_ACCESS_TOKEN", "")
    monkeypatch.setattr(settings, "WHATSAPP_TEMPLATE_NAME", "")
    body = client_admin.get("/api/notifications/whatsapp").json()
    assert body["connected"] is False
    assert body["enabled"] is False


def test_put_teams_then_get_round_trip_redacts_webhook(
    client_admin: TestClient,
) -> None:
    payload = {
        "enabled": False,
        "webhook_url": "https://example.webhook.office.com/workflows/abc",
        "channel_name": "Seguranca",
        "notify_on_confirmed": True,
    }
    res = client_admin.put("/api/notifications/teams", json=payload)
    assert res.status_code == 200, res.text
    assert "example.webhook.office.com" not in res.text
    body = res.json()
    assert body["has_webhook_url"] is True
    assert body["channel_name"] == "Seguranca"
    assert body["notify_on_confirmed"] is True

    res2 = client_admin.get("/api/notifications/teams")
    assert res2.status_code == 200
    assert "example.webhook.office.com" not in res2.text
    assert res2.json()["has_webhook_url"] is True


def test_put_rejects_enabling_when_not_connected(
    client_admin: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    # No global Meta credentials -> cannot enable.
    monkeypatch.setattr(settings, "WHATSAPP_PHONE_NUMBER_ID", "")
    monkeypatch.setattr(settings, "WHATSAPP_ACCESS_TOKEN", "")
    monkeypatch.setattr(settings, "WHATSAPP_TEMPLATE_NAME", "")
    res = client_admin.put(
        "/api/notifications/whatsapp",
        json={"enabled": True, "include_image": True},
    )
    assert res.status_code == 400
    assert "credenciais" in res.text.lower()


def test_put_teams_rejects_enabling_without_webhook(
    client_admin: TestClient,
) -> None:
    res = client_admin.put(
        "/api/notifications/teams",
        json={
            "enabled": True,
            "webhook_url": None,
            "channel_name": "Seguranca",
            "notify_on_confirmed": True,
        },
    )
    assert res.status_code == 400
    assert "webhook" in res.text.lower()


def test_put_teams_rejects_non_https_webhook(client_admin: TestClient) -> None:
    res = client_admin.put(
        "/api/notifications/teams",
        json={
            "enabled": False,
            "webhook_url": "http://example.test/hook",
            "channel_name": "Seguranca",
            "notify_on_confirmed": True,
        },
    )
    assert res.status_code == 422


def test_add_and_list_operator(client_admin: TestClient) -> None:
    res = client_admin.post(
        "/api/notifications/whatsapp/operators",
        json={"phone": "+5511999999999", "name": "Ana"},
    )
    assert res.status_code == 201, res.text
    op = res.json()
    assert op["phone"] == "+5511999999999"
    assert op["name"] == "Ana"
    assert op["enabled"] is True

    listed = client_admin.get("/api/notifications/whatsapp").json()["operators"]
    assert [o["phone"] for o in listed] == ["+5511999999999"]


def test_add_operator_validates_e164(client_admin: TestClient) -> None:
    res = client_admin.post(
        "/api/notifications/whatsapp/operators",
        json={"phone": "5511999999999"},  # missing +
    )
    assert res.status_code == 422


def test_add_operator_conflicts_across_tenant(
    client_admin: TestClient, test_db: sessionmaker[Session]
) -> None:
    # Another tenant already owns this phone.
    with test_db() as session:
        session.add(Tenant(id=OTHER_TENANT_ID, name="OTHER"))
        session.add(
            WhatsAppOperator(tenant_id=OTHER_TENANT_ID, phone="+5511777777777")
        )
        session.commit()

    res = client_admin.post(
        "/api/notifications/whatsapp/operators",
        json={"phone": "+5511777777777"},
    )
    assert res.status_code == 409
    assert "tenant" in res.text.lower()


def test_toggle_and_delete_operator(client_admin: TestClient) -> None:
    created = client_admin.post(
        "/api/notifications/whatsapp/operators",
        json={"phone": "+5511999999999", "name": "Ana"},
    ).json()
    op_id = created["id"]

    patched = client_admin.patch(
        f"/api/notifications/whatsapp/operators/{op_id}",
        json={"enabled": False},
    )
    assert patched.status_code == 200
    assert patched.json()["enabled"] is False

    deleted = client_admin.delete(
        f"/api/notifications/whatsapp/operators/{op_id}"
    )
    assert deleted.status_code == 204
    assert client_admin.get("/api/notifications/whatsapp").json()["operators"] == []


def test_put_teams_with_null_webhook_keeps_existing(
    client_admin: TestClient,
) -> None:
    client_admin.put(
        "/api/notifications/teams",
        json={
            "enabled": False,
            "webhook_url": "https://example.webhook.office.com/workflows/first",
            "channel_name": "Seguranca",
            "notify_on_confirmed": True,
        },
    )
    res = client_admin.put(
        "/api/notifications/teams",
        json={
            "enabled": True,
            "webhook_url": None,
            "channel_name": "CIPA",
            "notify_on_confirmed": False,
        },
    )
    assert res.status_code == 200, res.text
    assert res.json()["enabled"] is True
    assert res.json()["has_webhook_url"] is True
    assert res.json()["channel_name"] == "CIPA"
    assert res.json()["notify_on_confirmed"] is False


def test_viewer_cannot_access(client_viewer: TestClient) -> None:
    assert client_viewer.get("/api/notifications/whatsapp").status_code == 403
    assert client_viewer.get("/api/notifications/teams").status_code == 403
    assert (
        client_viewer.put(
            "/api/notifications/whatsapp",
            json={"enabled": False, "include_image": True},
        ).status_code
        == 403
    )
    assert (
        client_viewer.put(
            "/api/notifications/teams",
            json={
                "enabled": False,
                "webhook_url": None,
                "channel_name": None,
                "notify_on_confirmed": True,
            },
        ).status_code
        == 403
    )
