"""OpenAI-compatible chat completion client with provider failover.

DeepSeek is primary (cost-effective, OpenAI-compatible). OpenRouter is the
automatic fallback when the primary errors or is unconfigured. Both speak the
same `/chat/completions` schema, including tool calling.
"""

from __future__ import annotations

import httpx
import structlog

from app.config import settings
from app.observability import llm_fallback_total

log = structlog.get_logger(__name__)


class LLMError(RuntimeError):
    """Raised when no provider can fulfil a completion."""


class LLMUnavailableError(LLMError):
    """Raised when no provider is configured at all."""


def _deepseek_configured() -> bool:
    return bool(settings.DEEPSEEK_API_KEY.strip())


def _openrouter_configured() -> bool:
    return bool(settings.OPENROUTER_API_KEY.strip())


def llm_available() -> bool:
    return _deepseek_configured() or _openrouter_configured()


def _call(
    *,
    base_url: str,
    api_key: str,
    model: str,
    messages: list[dict],
    tools: list[dict] | None,
) -> dict:
    payload: dict = {"model": model, "messages": messages}
    if tools:
        payload["tools"] = tools
        payload["tool_choice"] = "auto"
    headers = {"Authorization": f"Bearer {api_key}"}
    with httpx.Client(timeout=settings.LLM_HTTP_TIMEOUT) as client:
        resp = client.post(
            f"{base_url}/chat/completions", headers=headers, json=payload
        )
        resp.raise_for_status()
        return resp.json()


def complete(messages: list[dict], tools: list[dict] | None = None) -> dict:
    """Return the assistant message dict from the first provider that succeeds."""
    if not llm_available():
        raise LLMUnavailableError(
            "No LLM provider configured. Set VIGILANTE_DEEPSEEK_API_KEY or "
            "VIGILANTE_OPENROUTER_API_KEY."
        )

    if _deepseek_configured():
        try:
            data = _call(
                base_url=settings.DEEPSEEK_BASE_URL,
                api_key=settings.DEEPSEEK_API_KEY,
                model=settings.LLM_MODEL,
                messages=messages,
                tools=tools,
            )
            return data["choices"][0]["message"]
        except Exception as exc:  # noqa: BLE001 - failover to OpenRouter
            log.warning("deepseek_failed", error=str(exc))
            if not _openrouter_configured():
                raise LLMError(f"DeepSeek failed and no fallback: {exc}") from exc
            llm_fallback_total.inc()

    # OpenRouter (fallback or primary if DeepSeek unconfigured).
    try:
        data = _call(
            base_url=settings.OPENROUTER_BASE_URL,
            api_key=settings.OPENROUTER_API_KEY,
            model=settings.LLM_FALLBACK_MODEL,
            messages=messages,
            tools=tools,
        )
        return data["choices"][0]["message"]
    except Exception as exc:  # noqa: BLE001
        log.error("openrouter_failed", error=str(exc))
        raise LLMError(f"All LLM providers failed: {exc}") from exc
