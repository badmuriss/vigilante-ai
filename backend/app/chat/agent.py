"""Agent loop: LLM <-> tools until a final text answer.

Stateless. Caller passes prior history; the loop appends the new user turn,
runs up to `CHAT_MAX_ITERATIONS` tool rounds (deduping identical calls), then
returns the final assistant text + collected citations + a tool-call trace.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field

import structlog

from app.chat import llm_client
from app.chat.prompts import build_system_prompt, validate_kb_citations
from app.chat.tools import ToolContext, ToolRegistry
from app.config import settings
from app.observability import chat_tool_calls_total

log = structlog.get_logger(__name__)


@dataclass
class AgentResult:
    content: str
    citations: list[dict] = field(default_factory=list)
    tool_calls: list[dict] = field(default_factory=list)
    artifacts: list[dict] = field(default_factory=list)


def _args_hash(name: str, raw_args: str) -> str:
    return hashlib.sha256(f"{name}:{raw_args}".encode()).hexdigest()


class AgentLoop:
    def __init__(self, registry: ToolRegistry) -> None:
        self._registry = registry

    def run(
        self,
        *,
        ctx: ToolContext,
        history: list[dict],
        user_message: str,
        channel: str = "ui",
    ) -> AgentResult:
        messages: list[dict] = [
            {"role": "system", "content": build_system_prompt(channel)},
            *_sanitize_history(history),
            {"role": "user", "content": user_message},
        ]
        tools = self._registry.openai_schemas()
        called: set[str] = set()
        citations: list[dict] = []
        artifacts: list[dict] = []
        trace: list[dict] = []
        retrieved_indices: set[int] = set()

        for _ in range(settings.CHAT_MAX_ITERATIONS):
            msg = llm_client.complete(messages, tools=tools)
            messages.append(_normalize_assistant(msg))

            tool_calls = msg.get("tool_calls") or []
            if not tool_calls:
                # Keep markdown — the UI renders it; the WhatsApp path strips it
                # before sending (split_for_whatsapp in the webhook handler).
                content = msg.get("content") or ""
                content = validate_kb_citations(content, retrieved_indices)
                return AgentResult(
                    content=content.strip(),
                    citations=citations,
                    tool_calls=trace,
                    artifacts=artifacts,
                )

            for tc in tool_calls:
                fn = tc.get("function", {})
                name = fn.get("name", "")
                raw_args = fn.get("arguments") or "{}"
                call_id = tc.get("id") or name
                key = _args_hash(name, raw_args)

                if key in called:
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": call_id,
                            "content": "[chamada repetida ignorada]",
                        }
                    )
                    continue
                called.add(key)

                try:
                    args = json.loads(raw_args) if raw_args.strip() else {}
                except json.JSONDecodeError:
                    args = {}

                try:
                    result = self._registry.dispatch(name, args, ctx)
                    chat_tool_calls_total.labels(tool=name, status="ok").inc()
                    if result.citations:
                        citations.extend(result.citations)
                        retrieved_indices.update(c["idx"] for c in result.citations)
                    if result.artifacts:
                        artifacts.extend(result.artifacts)
                    trace.append({"tool": name, "args": args})
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": call_id,
                            "content": json.dumps(result.payload, ensure_ascii=False),
                        }
                    )
                except Exception as exc:  # noqa: BLE001 - surface to model, keep going
                    chat_tool_calls_total.labels(tool=name, status="error").inc()
                    log.warning("tool_error", tool=name, error=str(exc))
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": call_id,
                            "content": f"ERROR: {exc}",
                        }
                    )

        # Hit the iteration cap — force a tool-free synthesis turn.
        messages.append(
            {
                "role": "system",
                "content": "Limite de ferramentas atingido. Responda com o que já tem.",
            }
        )
        final = llm_client.complete(messages, tools=None)
        content = validate_kb_citations(final.get("content") or "", retrieved_indices)
        return AgentResult(
            content=content.strip(),
            citations=citations,
            tool_calls=trace,
            artifacts=artifacts,
        )


def _sanitize_history(history: list[dict]) -> list[dict]:
    """Keep only role+content for prior turns (drop tool scaffolding/citations)."""
    out: list[dict] = []
    for m in history[-settings.CHAT_MAX_HISTORY_MESSAGES :]:
        role = m.get("role")
        if role not in ("user", "assistant"):
            continue
        content = m.get("content")
        if not content:
            continue
        out.append({"role": role, "content": content})
    return out


def _normalize_assistant(msg: dict) -> dict:
    """Keep what the API needs to continue the turn.

    DeepSeek thinking models (deepseek-v4-pro) require `reasoning_content` to be
    echoed back on the assistant turn that carried tool_calls, otherwise the
    follow-up request 400s ("reasoning_content ... must be passed back").
    """
    out: dict = {"role": "assistant", "content": msg.get("content") or ""}
    if msg.get("tool_calls"):
        out["tool_calls"] = msg["tool_calls"]
    if msg.get("reasoning_content"):
        out["reasoning_content"] = msg["reasoning_content"]
    return out
