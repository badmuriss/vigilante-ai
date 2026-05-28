"""ChatService — the convergence point.

Both the web UI (`POST /api/chat/messages`) and the WhatsApp inbound webhook
call `handle_message`. Same agent, same tools, same KB, same conversation
store. The only channel-specific bit (WA 400-char splitting) is left to the
caller, since `handle_message` returns the raw reply.
"""

from __future__ import annotations

import time
import uuid

import structlog
from sqlalchemy.orm import Session

from app.chat.agent import AgentLoop, AgentResult
from app.chat.history import ConversationRepository
from app.chat.tools import ToolContext, build_default_registry
from app.config import settings
from app.observability import chat_latency_seconds, chat_messages_total

log = structlog.get_logger(__name__)

# Registry is stateless across requests — build once.
_REGISTRY = build_default_registry()
_AGENT = AgentLoop(_REGISTRY)


class ChatReply:
    def __init__(self, conversation_id: str, result: AgentResult, latency_ms: int):
        self.conversation_id = conversation_id
        self.content = result.content
        self.citations = result.citations
        self.tool_calls = result.tool_calls
        self.charts = result.artifacts
        self.latency_ms = latency_ms


def handle_message(
    session: Session,
    *,
    tenant_id: str,
    channel: str,
    user_identifier: str,
    text: str,
    user_id: str | None = None,
    conversation_id: str | None = None,
) -> ChatReply:
    """Run one user turn through the agent and persist it. Caller commits."""
    repo = ConversationRepository(session)

    conv = None
    if conversation_id:
        conv = repo.get_for_tenant(conversation_id, tenant_id)
    if conv is None:
        if channel == "whatsapp":
            # One ongoing thread per phone number.
            conv = repo.get_or_create(
                tenant_id=tenant_id,
                channel=channel,
                user_identifier=user_identifier,
                user_id=user_id,
                title=text[:60],
            )
        else:
            # UI: each new chat is its own thread (linked to the user via
            # user_id); a fresh user_identifier keeps the uniqueness index happy.
            conv = repo.create(
                tenant_id=tenant_id,
                channel=channel,
                user_identifier=f"{user_id or user_identifier}:{uuid.uuid4()}",
                user_id=user_id,
                title=text[:60],
            )

    chat_messages_total.labels(channel=channel, role="user").inc()
    started = time.monotonic()
    result = _AGENT.run(
        ctx=ToolContext(tenant_id=tenant_id, session=session),
        history=list(conv.messages or []),
        user_message=text,
        channel=channel,
    )
    latency = time.monotonic() - started
    chat_latency_seconds.labels(channel=channel).observe(latency)
    chat_messages_total.labels(channel=channel, role="assistant").inc()

    repo.append_messages(
        conv,
        [
            {"role": "user", "content": text},
            {
                "role": "assistant",
                "content": result.content,
                "citations": result.citations,
                "tool_calls": result.tool_calls,
                "charts": result.artifacts,
            },
        ],
    )
    session.flush()

    log.info(
        "chat_turn",
        channel=channel,
        tenant_id=tenant_id,
        conversation_id=conv.id,
        latency_ms=int(latency * 1000),
        tools=[t["tool"] for t in result.tool_calls],
    )
    return ChatReply(conv.id, result, int(latency * 1000))
