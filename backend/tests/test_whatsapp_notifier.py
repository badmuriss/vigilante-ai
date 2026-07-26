"""Unit tests for the WhatsApp notifier service.

Covers:
- E.164 validator
- `_dispatch` skips when config disabled / missing / no operators
- `_dispatch` happy path: media upload + per-operator send (global creds)
- disabled operators are not sent to
- `send_test` returns Meta error verbatim on 4xx
- `notify_async` snapshots the alert and submits to executor

Tests use an in-memory SQLite DB and `httpx.MockTransport` so they run
without network and without touching the real Postgres. Meta credentials are
global (settings) and monkeypatched per test.
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Iterator

import httpx
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app import db
from app.config import settings
from app.db.base import Base
from app.db.entities import Camera, Site, Tenant, WhatsAppConfig, WhatsAppOperator
from app.services.whatsapp_notifier import WhatsAppNotifier, is_e164
from app.storage import BlobStore


# ---------- fixtures ----------


class FakeBlobStore(BlobStore):  # type: ignore[misc]
    """Minimal in-memory BlobStore for tests."""

    def __init__(self, frames: dict[str, bytes] | None = None) -> None:
        self._frames = frames or {}

    def save_jpeg(self, *, camera_id: str, alert_id: str, kind: str, data: bytes) -> str:
        path = f"{camera_id}/{alert_id}_{kind}.jpg"
        self._frames[path] = data
        return path

    def load_bytes(self, path: str) -> bytes | None:
        return self._frames.get(path)

    def delete(self, path: str) -> None:
        self._frames.pop(path, None)


@pytest.fixture()
def wa_creds(monkeypatch: pytest.MonkeyPatch) -> None:
    """Configure the single shared platform Meta number via settings."""
    monkeypatch.setattr(settings, "WHATSAPP_PHONE_NUMBER_ID", "111222333")
    monkeypatch.setattr(settings, "WHATSAPP_ACCESS_TOKEN", "META_TOKEN")
    monkeypatch.setattr(settings, "WHATSAPP_APP_SECRET", "appsecret")
    monkeypatch.setattr(settings, "WHATSAPP_VERIFY_TOKEN", "verifytoken")
    monkeypatch.setattr(settings, "WHATSAPP_TEMPLATE_NAME", "safety_alert_pt")
    monkeypatch.setattr(settings, "WHATSAPP_TEMPLATE_LANGUAGE", "pt_BR")
    monkeypatch.setattr(settings, "LOCAL_TIMEZONE", "America/Sao_Paulo")


@pytest.fixture()
def test_db(monkeypatch: pytest.MonkeyPatch) -> Iterator[sessionmaker[Session]]:
    """Replace the global engine/session factory with an in-memory SQLite."""
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
    # whatsapp_notifier module captured `session_scope` at import time.
    from app.services import whatsapp_notifier as wn

    monkeypatch.setattr(wn, "session_scope", lambda: factory())

    yield factory
    engine.dispose()


@pytest.fixture()
def seeded_tenant(
    test_db: sessionmaker[Session], wa_creds: None
) -> tuple[str, str, str]:
    """Insert tenant + site + camera + WhatsAppConfig + 2 operators.

    Returns (tenant_id, camera_id, frame_path)."""
    with test_db() as session:
        tenant = Tenant(name="ACME")
        session.add(tenant)
        session.flush()
        site = Site(tenant_id=tenant.id, name="HQ")
        session.add(site)
        session.flush()
        camera = Camera(
            site_id=site.id,
            name="Portao Norte",
            source_kind="rtsp",
            rtsp_url="rtsp://test",
        )
        session.add(camera)
        session.flush()
        session.add(
            WhatsAppConfig(tenant_id=tenant.id, enabled=True, include_image=True)
        )
        session.add(
            WhatsAppOperator(
                tenant_id=tenant.id, phone="+5511999999999", name="Ana", enabled=True
            )
        )
        session.add(
            WhatsAppOperator(
                tenant_id=tenant.id, phone="+5511888888888", name=None, enabled=True
            )
        )
        session.commit()
        return str(tenant.id), str(camera.id), "fakeframe.jpg"


def _make_alert_snapshot(camera_id: str, frame_path: str | None):
    from app.services.whatsapp_notifier import _AlertSnapshot

    return _AlertSnapshot(
        id="alert-123",
        camera_id=camera_id,
        violation_type="capacete_ausente",
        missing_epis=["capacete"],
        timestamp=datetime(2026, 5, 25, 14, 30),
        frame_path=frame_path,
    )


# ---------- E.164 ----------


@pytest.mark.parametrize(
    "value,expected",
    [
        ("+5511999999999", True),
        ("+12025551234", True),
        ("5511999999999", False),  # no leading +
        ("+0511999999999", False),  # leading zero after +
        ("+abc", False),
        ("", False),
        ("+12345", False),  # too short
        ("+1234567890123456", False),  # too long
    ],
)
def test_is_e164(value: str, expected: bool) -> None:
    assert is_e164(value) is expected


# ---------- _dispatch ----------


def test_dispatch_skips_when_config_missing(
    test_db: sessionmaker[Session], wa_creds: None
) -> None:
    # Tenant + camera exist but no WhatsAppConfig row.
    with test_db() as session:
        tenant = Tenant(name="NoConfig")
        session.add(tenant)
        session.flush()
        site = Site(tenant_id=tenant.id, name="S")
        session.add(site)
        session.flush()
        camera = Camera(site_id=site.id, name="C", source_kind="rtsp", rtsp_url="x")
        session.add(camera)
        session.commit()
        camera_id = str(camera.id)

    captured: list[httpx.Request] = []

    def handler(req: httpx.Request) -> httpx.Response:
        captured.append(req)
        return httpx.Response(200, json={"messages": [{"id": "m1"}]})

    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport, base_url="https://graph.test")
    notifier = WhatsAppNotifier(FakeBlobStore(), http_client=client, max_workers=1)
    notifier._dispatch(_make_alert_snapshot(camera_id, None))
    notifier.shutdown(wait=False)

    assert captured == []  # no HTTP calls when config missing


def test_dispatch_skips_when_no_operators(
    test_db: sessionmaker[Session], wa_creds: None
) -> None:
    with test_db() as session:
        tenant = Tenant(name="NoOps")
        session.add(tenant)
        session.flush()
        site = Site(tenant_id=tenant.id, name="S")
        session.add(site)
        session.flush()
        camera = Camera(site_id=site.id, name="C", source_kind="rtsp", rtsp_url="x")
        session.add(camera)
        session.flush()
        session.add(
            WhatsAppConfig(tenant_id=tenant.id, enabled=True, include_image=True)
        )
        session.commit()
        camera_id = str(camera.id)

    captured: list[httpx.Request] = []

    def handler(req: httpx.Request) -> httpx.Response:
        captured.append(req)
        return httpx.Response(200, json={"messages": [{"id": "m1"}]})

    client = httpx.Client(
        transport=httpx.MockTransport(handler), base_url="https://graph.test"
    )
    notifier = WhatsAppNotifier(FakeBlobStore(), http_client=client, max_workers=1)
    notifier._dispatch(_make_alert_snapshot(camera_id, None))
    notifier.shutdown(wait=False)

    assert captured == []


def test_dispatch_happy_path_uploads_once_and_sends_per_operator(
    seeded_tenant: tuple[str, str, str],
    test_db: sessionmaker[Session],
) -> None:
    tenant_id, camera_id, frame_path = seeded_tenant
    blob_store = FakeBlobStore({frame_path: b"\xff\xd8\xff\xe0fakejpeg"})

    captured: list[httpx.Request] = []

    def handler(req: httpx.Request) -> httpx.Response:
        captured.append(req)
        if req.url.path.endswith("/media"):
            return httpx.Response(200, json={"id": "media-xyz"})
        return httpx.Response(200, json={"messages": [{"id": f"wamid-{len(captured)}"}]})

    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport, base_url="https://graph.test")
    notifier = WhatsAppNotifier(blob_store, http_client=client, max_workers=1)

    notifier._dispatch(_make_alert_snapshot(camera_id, frame_path))
    notifier.shutdown(wait=False)

    # 1 upload + 2 sends (one per enabled operator), via the global number.
    assert len(captured) == 3
    assert captured[0].url.path.endswith("/111222333/media")
    for req in captured[1:]:
        assert req.url.path.endswith("/111222333/messages")
        body = json.loads(req.content)
        assert body["type"] == "template"
        assert body["to"] in {"5511999999999", "5511888888888"}
        assert body["template"]["name"] == "safety_alert_pt"
        components = body["template"]["components"]
        header = next(c for c in components if c["type"] == "header")
        assert header["parameters"][0]["image"]["id"] == "media-xyz"
        body_comp = next(c for c in components if c["type"] == "body")
        assert [p["text"] for p in body_comp["parameters"]] == [
            "Portao Norte",
            "Capacete",
            "25/05/2026 11:30",
        ]


def test_dispatch_skips_disabled_operators(
    seeded_tenant: tuple[str, str, str],
    test_db: sessionmaker[Session],
) -> None:
    tenant_id, camera_id, frame_path = seeded_tenant
    with test_db() as session:
        op = (
            session.query(WhatsAppOperator)
            .filter(WhatsAppOperator.phone == "+5511888888888")
            .first()
        )
        assert op is not None
        op.enabled = False
        session.commit()

    sent_to: list[str] = []

    def handler(req: httpx.Request) -> httpx.Response:
        if req.url.path.endswith("/messages"):
            sent_to.append(json.loads(req.content)["to"])
        return httpx.Response(200, json={"messages": [{"id": "x"}]})

    client = httpx.Client(
        transport=httpx.MockTransport(handler), base_url="https://graph.test"
    )
    notifier = WhatsAppNotifier(FakeBlobStore(), http_client=client, max_workers=1)
    notifier._dispatch(_make_alert_snapshot(camera_id, None))
    notifier.shutdown(wait=False)

    assert sent_to == ["5511999999999"]


def test_dispatch_skips_when_disabled(
    seeded_tenant: tuple[str, str, str],
    test_db: sessionmaker[Session],
) -> None:
    tenant_id, camera_id, frame_path = seeded_tenant
    with test_db() as session:
        cfg = session.query(WhatsAppConfig).first()
        assert cfg is not None
        cfg.enabled = False
        session.commit()

    captured: list[httpx.Request] = []

    def handler(req: httpx.Request) -> httpx.Response:
        captured.append(req)
        return httpx.Response(200, json={"messages": [{"id": "x"}]})

    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport, base_url="https://graph.test")
    notifier = WhatsAppNotifier(
        FakeBlobStore({frame_path: b"x"}), http_client=client, max_workers=1
    )
    notifier._dispatch(_make_alert_snapshot(camera_id, frame_path))
    notifier.shutdown(wait=False)

    assert captured == []


def test_dispatch_text_only_when_include_image_false(
    seeded_tenant: tuple[str, str, str],
    test_db: sessionmaker[Session],
) -> None:
    tenant_id, camera_id, frame_path = seeded_tenant
    with test_db() as session:
        cfg = session.query(WhatsAppConfig).first()
        assert cfg is not None
        cfg.include_image = False
        # keep only one operator so the assertion is unambiguous
        op = (
            session.query(WhatsAppOperator)
            .filter(WhatsAppOperator.phone == "+5511888888888")
            .first()
        )
        session.delete(op)
        session.commit()

    requests: list[httpx.Request] = []

    def handler(req: httpx.Request) -> httpx.Response:
        requests.append(req)
        return httpx.Response(200, json={"messages": [{"id": "wamid-1"}]})

    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport, base_url="https://graph.test")
    notifier = WhatsAppNotifier(
        FakeBlobStore({frame_path: b"x"}), http_client=client, max_workers=1
    )
    notifier._dispatch(_make_alert_snapshot(camera_id, frame_path))
    notifier.shutdown(wait=False)

    assert len(requests) == 1
    assert requests[0].url.path.endswith("/messages")
    body = json.loads(requests[0].content)
    components = body["template"]["components"]
    assert all(c["type"] != "header" for c in components)


def test_dispatch_review_includes_buttons(
    seeded_tenant: tuple[str, str, str],
    test_db: sessionmaker[Session],
) -> None:
    tenant_id, camera_id, frame_path = seeded_tenant
    sent: list[dict] = []

    def handler(req: httpx.Request) -> httpx.Response:
        if req.url.path.endswith("/messages"):
            sent.append(json.loads(req.content))
        return httpx.Response(200, json={"messages": [{"id": "x"}]})

    client = httpx.Client(
        transport=httpx.MockTransport(handler), base_url="https://graph.test"
    )
    notifier = WhatsAppNotifier(FakeBlobStore(), http_client=client, max_workers=1)
    snap = _make_alert_snapshot(camera_id, None)
    notifier._dispatch(snap, with_buttons=True)
    notifier.shutdown(wait=False)

    assert sent  # one per enabled operator
    btns = [c for c in sent[0]["template"]["components"] if c["type"] == "button"]
    assert [c["sub_type"] for c in btns] == ["quick_reply", "quick_reply"]
    assert btns[0]["index"] == "0"
    assert btns[0]["parameters"][0]["payload"] == f"confirm:{snap.id}"
    assert btns[1]["index"] == "1"
    assert btns[1]["parameters"][0]["payload"] == f"false_positive:{snap.id}"


def test_dispatch_default_has_no_buttons(
    seeded_tenant: tuple[str, str, str],
    test_db: sessionmaker[Session],
) -> None:
    tenant_id, camera_id, frame_path = seeded_tenant
    sent: list[dict] = []

    def handler(req: httpx.Request) -> httpx.Response:
        if req.url.path.endswith("/messages"):
            sent.append(json.loads(req.content))
        return httpx.Response(200, json={"messages": [{"id": "x"}]})

    client = httpx.Client(
        transport=httpx.MockTransport(handler), base_url="https://graph.test"
    )
    notifier = WhatsAppNotifier(FakeBlobStore(), http_client=client, max_workers=1)
    notifier._dispatch(_make_alert_snapshot(camera_id, None))
    notifier.shutdown(wait=False)

    assert sent
    assert not [c for c in sent[0]["template"]["components"] if c["type"] == "button"]


# ---------- send_test ----------


def test_send_test_returns_meta_error_on_400(
    seeded_tenant: tuple[str, str, str],
    test_db: sessionmaker[Session],
) -> None:
    tenant_id, camera_id, _ = seeded_tenant

    def handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(
            400,
            json={"error": {"message": "invalid template", "code": 132001}},
        )

    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport, base_url="https://graph.test")
    notifier = WhatsAppNotifier(FakeBlobStore(), http_client=client, max_workers=1)

    result = notifier.send_test(tenant_id=tenant_id, phone_number="+5511999999999")
    notifier.shutdown(wait=False)

    assert result["ok"] is False
    assert "invalid template" in (result.get("error") or "")


def test_send_test_uses_global_creds(
    seeded_tenant: tuple[str, str, str],
    test_db: sessionmaker[Session],
) -> None:
    tenant_id, _camera_id, _ = seeded_tenant

    requests: list[httpx.Request] = []

    def handler(req: httpx.Request) -> httpx.Response:
        requests.append(req)
        return httpx.Response(200, json={"messages": [{"id": "wamid-test"}]})

    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport, base_url="https://graph.test")
    notifier = WhatsAppNotifier(FakeBlobStore(), http_client=client, max_workers=1)

    result = notifier.send_test(tenant_id=tenant_id, phone_number="+5511999999999")
    notifier.shutdown(wait=False)

    assert result == {"ok": True, "message_id": "wamid-test"}
    assert len(requests) == 1
    assert requests[0].url.path.endswith("/111222333/messages")
    assert json.loads(requests[0].content)["to"] == "5511999999999"


def test_send_test_fails_when_not_connected(
    test_db: sessionmaker[Session], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "WHATSAPP_PHONE_NUMBER_ID", "")
    monkeypatch.setattr(settings, "WHATSAPP_ACCESS_TOKEN", "")
    monkeypatch.setattr(settings, "WHATSAPP_TEMPLATE_NAME", "")

    notifier = WhatsAppNotifier(FakeBlobStore(), max_workers=1)
    result = notifier.send_test(tenant_id="t", phone_number="+5511999999999")
    notifier.shutdown(wait=False)

    assert result["ok"] is False
    assert "WHATSAPP_PHONE_NUMBER_ID" in (result.get("error") or "")


# ---------- notify_async ----------


def test_notify_async_does_not_raise_when_executor_closed(
    seeded_tenant: tuple[str, str, str],
    test_db: sessionmaker[Session],
) -> None:
    tenant_id, camera_id, frame_path = seeded_tenant
    blob_store = FakeBlobStore({frame_path: b"x"})

    def handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"messages": [{"id": "x"}]})

    notifier = WhatsAppNotifier(
        blob_store,
        http_client=httpx.Client(transport=httpx.MockTransport(handler), base_url="https://graph.test"),
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
            "timestamp": datetime(2026, 5, 25, 0, 0),
            "frame_path": None,
        },
    )()

    # Should swallow the closed-executor case without raising.
    notifier.notify_async(fake_alert)  # type: ignore[arg-type]
