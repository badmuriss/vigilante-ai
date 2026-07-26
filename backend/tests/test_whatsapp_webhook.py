"""Tests for the inbound WhatsApp webhook — the convergence point.

Focus: the single shared number means the tenant is resolved from the SENDER's
phone via `whatsapp_operators`, and the verify/signature checks run against the
global (settings) credentials.
"""

from __future__ import annotations

import sys
import types
from typing import Iterator

import hashlib
import hmac
import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app import db
from app.config import settings
from app.db.base import Base
from app.db.entities import Alert, Camera, Site, Tenant, WhatsAppOperator
from app.webhooks import whatsapp as wh


@pytest.fixture()
def test_db(monkeypatch: pytest.MonkeyPatch) -> Iterator[sessionmaker[Session]]:
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, future=True
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False, future=True)
    monkeypatch.setattr(db.base, "session_scope", lambda: factory())
    # The webhook module captured `session_scope` at import time.
    monkeypatch.setattr(wh, "session_scope", lambda: factory())
    yield factory
    engine.dispose()


@pytest.fixture()
def seeded(test_db: sessionmaker[Session]) -> str:
    with test_db() as session:
        tenant = Tenant(name="ACME")
        session.add(tenant)
        session.flush()
        session.add(
            WhatsAppOperator(
                tenant_id=tenant.id, phone="+5511999999999", enabled=True
            )
        )
        session.commit()
        return str(tenant.id)


# ---------- verify handshake ----------


def test_verify_ok(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "WHATSAPP_VERIFY_TOKEN", "secret-verify")
    resp = wh.verify_webhook(
        hub_mode="subscribe",
        hub_verify_token="secret-verify",
        hub_challenge="ping",
    )
    assert resp.body == b"ping"


def test_verify_mismatch(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "WHATSAPP_VERIFY_TOKEN", "secret-verify")
    with pytest.raises(HTTPException) as exc:
        wh.verify_webhook(
            hub_mode="subscribe", hub_verify_token="wrong", hub_challenge="ping"
        )
    assert exc.value.status_code == 403


def test_verify_non_ascii_token_is_403_not_500(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # hmac.compare_digest raises TypeError on non-ASCII str; must stay a 403.
    monkeypatch.setattr(settings, "WHATSAPP_VERIFY_TOKEN", "secret-verify")
    with pytest.raises(HTTPException) as exc:
        wh.verify_webhook(
            hub_mode="subscribe", hub_verify_token="töken", hub_challenge="ping"
        )
    assert exc.value.status_code == 403


def test_signature_non_ascii_header_returns_false(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "WHATSAPP_APP_SECRET", "appsecret")
    assert wh._signature_ok(b"x", "sha256=ÿ") is False


# ---------- signature ----------


def test_signature_ok(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "WHATSAPP_APP_SECRET", "appsecret")
    raw = b'{"hello":"world"}'
    sig = "sha256=" + hmac.new(b"appsecret", raw, hashlib.sha256).hexdigest()
    assert wh._signature_ok(raw, sig) is True
    assert wh._signature_ok(raw, "sha256=deadbeef") is False


def test_signature_rejected_when_secret_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "WHATSAPP_APP_SECRET", "")
    assert wh._signature_ok(b"x", "sha256=whatever") is False


# ---------- tenant resolution by sender phone ----------


def test_inbound_resolves_tenant_from_operator(
    seeded: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    tenant_id = seeded
    calls: list[dict] = []
    sent: list[str] = []

    class _Reply:
        content = "olá"

    def fake_handle(session, *, tenant_id, channel, user_identifier, text):  # type: ignore[no-untyped-def]
        calls.append(
            {
                "tenant_id": tenant_id,
                "channel": channel,
                "user_identifier": user_identifier,
                "text": text,
            }
        )
        return _Reply()

    monkeypatch.setattr(wh.service, "handle_message", fake_handle)
    monkeypatch.setattr(wh, "send_session_text", lambda *, to, body: sent.append(to) or {"ok": True})

    wh._process_message(
        {"from": "5511999999999", "type": "text", "text": {"body": "oi"}, "id": "m1"}
    )

    assert len(calls) == 1
    assert calls[0]["tenant_id"] == tenant_id
    assert calls[0]["channel"] == "whatsapp"
    assert calls[0]["user_identifier"] == "5511999999999"
    assert sent == ["5511999999999"]


def test_inbound_drops_unknown_number(
    seeded: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[dict] = []

    def fake_handle(session, **kwargs):  # type: ignore[no-untyped-def]
        calls.append(kwargs)
        return None

    monkeypatch.setattr(wh.service, "handle_message", fake_handle)
    monkeypatch.setattr(wh, "send_session_text", lambda *, to, body: {"ok": True})

    wh._process_message(
        {"from": "5511000000000", "type": "text", "text": {"body": "oi"}, "id": "m2"}
    )

    assert calls == []  # unregistered sender -> no agent invocation


def test_inbound_drops_disabled_operator(
    seeded: str, test_db: sessionmaker[Session], monkeypatch: pytest.MonkeyPatch
) -> None:
    with test_db() as session:
        op = session.query(WhatsAppOperator).first()
        op.enabled = False
        session.commit()

    calls: list[dict] = []
    monkeypatch.setattr(
        wh.service, "handle_message", lambda session, **k: calls.append(k)
    )
    monkeypatch.setattr(wh, "send_session_text", lambda *, to, body: {"ok": True})

    wh._process_message(
        {"from": "5511999999999", "type": "text", "text": {"body": "oi"}, "id": "m3"}
    )
    assert calls == []


# ---------- review buttons ----------


def _seed_alert(factory: sessionmaker[Session], tenant_id: str) -> str:
    with factory() as session:
        site = Site(tenant_id=tenant_id, name="HQ")
        session.add(site)
        session.flush()
        cam = Camera(site_id=site.id, name="C", source_kind="rtsp", rtsp_url="x")
        session.add(cam)
        session.flush()
        alert = Alert(
            camera_id=cam.id,
            violation_type="capacete_ausente",
            confidence=0.9,
            missing_epis=["capacete"],
        )
        session.add(alert)
        session.commit()
        return str(alert.id)


@pytest.fixture()
def stub_retraining(monkeypatch: pytest.MonkeyPatch) -> None:
    # _handle_review_button lazy-imports app.main.retraining_exporter; stub it so
    # the test never loads the heavy app.main (detector/models).
    monkeypatch.setitem(
        sys.modules,
        "app.main",
        types.SimpleNamespace(
            retraining_exporter=types.SimpleNamespace(export=lambda a: None)
        ),
    )


def test_button_confirm_sets_feedback(
    seeded: str,
    test_db: sessionmaker[Session],
    stub_retraining: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    alert_id = _seed_alert(test_db, seeded)
    sent: list[str] = []
    monkeypatch.setattr(wh, "send_session_text", lambda *, to, body: sent.append(body) or {"ok": True})

    wh._handle_review_button(seeded, "5511999999999", f"confirm:{alert_id}")

    with test_db() as s:
        assert s.get(Alert, alert_id).feedback == "correct"
    assert sent and "confirmada" in sent[-1].lower()


def test_button_false_positive_sets_feedback(
    seeded: str,
    test_db: sessionmaker[Session],
    stub_retraining: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    alert_id = _seed_alert(test_db, seeded)
    monkeypatch.setattr(wh, "send_session_text", lambda *, to, body: {"ok": True})

    wh._handle_review_button(seeded, "5511999999999", f"false_positive:{alert_id}")

    with test_db() as s:
        assert s.get(Alert, alert_id).feedback == "false_positive"


def test_button_rejects_other_tenant(
    seeded: str,
    test_db: sessionmaker[Session],
    stub_retraining: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    alert_id = _seed_alert(test_db, seeded)
    # A different tenant taps the button -> must not apply.
    with test_db() as s:
        other = Tenant(name="OTHER")
        s.add(other)
        s.commit()
        other_id = str(other.id)
    sent: list[str] = []
    monkeypatch.setattr(wh, "send_session_text", lambda *, to, body: sent.append(body) or {"ok": True})

    wh._handle_review_button(other_id, "5511777777777", f"confirm:{alert_id}")

    with test_db() as s:
        assert s.get(Alert, alert_id).feedback is None
    assert sent and "acesso" in sent[-1].lower()


def test_button_unknown_payload_noop(
    seeded: str,
    test_db: sessionmaker[Session],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sent: list[str] = []
    monkeypatch.setattr(wh, "send_session_text", lambda *, to, body: sent.append(body) or {"ok": True})
    wh._handle_review_button(seeded, "5511999999999", "garbage")
    assert sent and "não entendi" in sent[-1].lower()
