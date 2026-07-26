"""Health probe endpoints for Kubernetes liveness/readiness.

`/healthz` must respond even with the DB down (it's the liveness probe -
depending on the DB there would restart the pod in a loop). The TestClient
is used *without* the `with` context manager, so the app's lifespan
(migrations, DB connect) never runs — proving `/healthz` needs none of it.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app


def test_healthz_ok_without_db() -> None:
    client = TestClient(app)  # no `with`: lifespan/startup never runs
    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_readyz_not_ready_without_db_or_model() -> None:
    client = TestClient(app)
    resp = client.get("/readyz")
    body = resp.json()
    assert resp.status_code == 503
    assert body["ready"] is False
    assert body["model"] is False
