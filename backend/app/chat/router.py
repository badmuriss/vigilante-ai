"""Chat API — authenticated web UI channel into the conversational HUB."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app.auth.dependencies import CurrentUser, get_current_user
from app.chat import service
from app.chat.history import ConversationRepository
from app.chat.llm_client import LLMUnavailableError
from app.chat.schemas import (
    AssistantMessage,
    ChartArtifact,
    ChatMessageRequest,
    ChatMessageResponse,
    Citation,
    ConversationDetail,
    ConversationListResponse,
    ConversationMessage,
    ConversationSummary,
    ToolCallSummary,
)
from app.db.base import get_session

router = APIRouter(prefix="/api/chat", tags=["chat"])


def _preview(messages: list[dict]) -> str:
    for m in reversed(messages or []):
        if m.get("content"):
            return str(m["content"])[:120]
    return ""


@router.post("/messages", response_model=ChatMessageResponse)
def post_message(
    req: ChatMessageRequest,
    user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ChatMessageResponse:
    try:
        reply = service.handle_message(
            session,
            tenant_id=user.tenant_id,
            channel="ui",
            user_identifier=user.id,
            user_id=user.id,
            text=req.message,
            conversation_id=req.conversation_id,
        )
    except LLMUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    session.commit()
    return ChatMessageResponse(
        conversation_id=reply.conversation_id,
        assistant_message=AssistantMessage(
            content=reply.content,
            citations=[Citation(**c) for c in reply.citations],
            tool_calls=[ToolCallSummary(**t) for t in reply.tool_calls],
            charts=[ChartArtifact(**c) for c in reply.charts],
        ),
        latency_ms=reply.latency_ms,
    )


@router.get("/conversations", response_model=ConversationListResponse)
def list_conversations(
    user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ConversationListResponse:
    convs = ConversationRepository(session).list_for_user(
        tenant_id=user.tenant_id, user_id=user.id
    )
    return ConversationListResponse(
        conversations=[
            ConversationSummary(
                id=c.id,
                title=c.title,
                channel=c.channel,
                updated_at=c.updated_at,
                last_message_preview=_preview(c.messages),
            )
            for c in convs
        ]
    )


@router.get("/conversations/{conversation_id}", response_model=ConversationDetail)
def get_conversation(
    conversation_id: str,
    user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ConversationDetail:
    conv = ConversationRepository(session).get_for_tenant(
        conversation_id, user.tenant_id
    )
    if conv is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return ConversationDetail(
        id=conv.id,
        title=conv.title,
        channel=conv.channel,
        updated_at=conv.updated_at,
        messages=[
            ConversationMessage(
                role=m.get("role", "assistant"),
                content=m.get("content", ""),
                citations=[Citation(**c) for c in m.get("citations", [])],
                tool_calls=[ToolCallSummary(**t) for t in m.get("tool_calls", [])],
                charts=[ChartArtifact(**c) for c in m.get("charts", [])],
            )
            for m in (conv.messages or [])
        ],
    )


@router.delete("/conversations/{conversation_id}", status_code=204)
def delete_conversation(
    conversation_id: str,
    user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> Response:
    repo = ConversationRepository(session)
    conv = repo.get_for_tenant(conversation_id, user.tenant_id)
    if conv is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    session.delete(conv)
    session.commit()
    return Response(status_code=204)
