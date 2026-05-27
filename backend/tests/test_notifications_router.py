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
from app.db.entities import Tenant
from app.notifications.router import router as notifications_router
from app.services import crypto


TEST_TENANT_ID = "00000000-0000-0000-0000-000000000001"


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
    assert body["has_token"] is False
    assert body["recipients"] == []

    teams_res = client_admin.get("/api/notifications/teams")
    assert teams_res.status_code == 200
    teams_body = teams_res.json()
    assert teams_body["enabled"] is False
    assert teams_body["has_webhook_url"] is False
    assert teams_body["notify_on_confirmed"] is True


def test_put_then_get_round_trip_redacts_token(client_admin: TestClient) -> None:
    payload = {
        "enabled": False,
        "phone_number_id": "111222",
        "access_token": "META_TOKEN",
        "template_name": "safety_alert_pt",
        "template_language": "pt_BR",
        "recipients": ["+5511999999999"],
        "include_image": True,
    }
    res = client_admin.put("/api/notifications/whatsapp", json=payload)
    assert res.status_code == 200, res.text
    body = res.json()
    # Token must NEVER leak in any field of the response.
    assert "META_TOKEN" not in res.text
    assert body["has_token"] is True
    assert body["phone_number_id"] == "111222"
    assert body["recipients"] == ["+5511999999999"]

    # GET returns same shape, still redacted.
    res2 = client_admin.get("/api/notifications/whatsapp")
    assert res2.status_code == 200
    assert "META_TOKEN" not in res2.text
    assert res2.json()["has_token"] is True


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


def test_put_rejects_enabling_without_token(client_admin: TestClient) -> None:
    res = client_admin.put(
        "/api/notifications/whatsapp",
        json={
            "enabled": True,
            "phone_number_id": "111",
            "access_token": None,
            "template_name": "t",
            "template_language": "pt_BR",
            "recipients": ["+5511999999999"],
            "include_image": True,
        },
    )
    assert res.status_code == 400
    assert "token" in res.text.lower()


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


def test_put_rejects_enabling_without_recipients(client_admin: TestClient) -> None:
    res = client_admin.put(
        "/api/notifications/whatsapp",
        json={
            "enabled": True,
            "phone_number_id": "111",
            "access_token": "ABC",
            "template_name": "t",
            "template_language": "pt_BR",
            "recipients": [],
            "include_image": True,
        },
    )
    assert res.status_code == 400
    assert "recipient" in res.text.lower()


def test_put_validates_e164(client_admin: TestClient) -> None:
    res = client_admin.put(
        "/api/notifications/whatsapp",
        json={
            "enabled": False,
            "phone_number_id": "111",
            "access_token": "ABC",
            "template_name": "t",
            "template_language": "pt_BR",
            "recipients": ["5511999999999"],  # missing +
            "include_image": True,
        },
    )
    assert res.status_code == 422


def test_put_with_null_token_keeps_existing(client_admin: TestClient) -> None:
    # First set a token.
    client_admin.put(
        "/api/notifications/whatsapp",
        json={
            "enabled": False,
            "phone_number_id": "111",
            "access_token": "FIRST_TOKEN",
            "template_name": "t",
            "template_language": "pt_BR",
            "recipients": ["+5511999999999"],
            "include_image": True,
        },
    )
    # Then update everything *except* the token (null).
    res = client_admin.put(
        "/api/notifications/whatsapp",
        json={
            "enabled": False,
            "phone_number_id": "222",
            "access_token": None,
            "template_name": "t2",
            "template_language": "pt_BR",
            "recipients": ["+5511888888888"],
            "include_image": False,
        },
    )
    assert res.status_code == 200
    assert res.json()["has_token"] is True
    assert res.json()["phone_number_id"] == "222"
    assert res.json()["recipients"] == ["+5511888888888"]


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
            json={
                "enabled": False,
                "phone_number_id": None,
                "access_token": None,
                "template_name": None,
                "template_language": "pt_BR",
                "recipients": [],
                "include_image": True,
            },
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
