"""Os proxies legados precisam repassar o usuário resolvido.

Regressão: `/api/alerts` e `/api/stats` chamavam as rotas por câmera como
função Python comum, sem passar `user`. O FastAPI só resolve `Depends` quando é
ele quem invoca a rota, então o parâmetro chegava como o próprio objeto
`Depends` e `_ensure_owns_camera` estourava com
`AttributeError: 'Depends' object has no attribute 'tenant_id'`, virando 500.
"""

from __future__ import annotations

from typing import Any, Callable

import pytest

import app.main as main


class _Cam:
    id = "cam-legacy"


def _forwards_user(
    monkeypatch: pytest.MonkeyPatch,
    endpoint: Callable[..., Any],
    target: str,
) -> None:
    """Chama o proxy e afirma que o `user` recebido chegou no destino."""
    seen: dict[str, Any] = {}

    def fake(camera_id: str, session: Any = None, user: Any = None, **_: Any) -> str:
        seen["camera_id"] = camera_id
        seen["user"] = user
        return "ok"

    monkeypatch.setattr(main, "_ensure_legacy_camera", lambda: _Cam())
    monkeypatch.setattr(main, target, fake)

    sentinel = object()
    assert endpoint(session=None, user=sentinel) == "ok"
    assert seen["camera_id"] == "cam-legacy"
    # O ponto do teste: tem que ser o objeto que entrou, nunca um Depends.
    assert seen["user"] is sentinel


class TestLegacyProxiesForwardUser:
    def test_get_alerts(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _forwards_user(monkeypatch, main.get_alerts, "list_camera_alerts")

    def test_clear_alerts(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _forwards_user(monkeypatch, main.clear_alerts, "clear_camera_alerts")

    def test_get_stats(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _forwards_user(monkeypatch, main.get_stats_endpoint, "get_camera_stats")

    @pytest.mark.parametrize(
        "endpoint",
        [main.get_alerts, main.clear_alerts, main.get_stats_endpoint],
        ids=["get_alerts", "clear_alerts", "get_stats"],
    )
    def test_declares_user_dependency(self, endpoint: Callable[..., Any]) -> None:
        """Sem o parâmetro `user`, o FastAPI nunca injeta e o bug volta."""
        import inspect

        assert "user" in inspect.signature(endpoint).parameters
