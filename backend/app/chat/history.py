"""Conversation persistence — JSONB message array per (tenant, channel, user).

The agent is stateless; the full thread lives in `conversations.messages`.
Appending mutates the array and bumps `updated_at`. We read-modify-write the
whole array (threads are small) to stay portable across Postgres + SQLite.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import desc, select
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from app.db.entities import Conversation


class ConversationRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, conversation_id: str) -> Conversation | None:
        return self._session.get(Conversation, conversation_id)

    def get_for_tenant(self, conversation_id: str, tenant_id: str) -> Conversation | None:
        return self._session.scalar(
            select(Conversation).where(
                Conversation.id == conversation_id,
                Conversation.tenant_id == tenant_id,
            )
        )

    def create(
        self,
        *,
        tenant_id: str,
        channel: str,
        user_identifier: str,
        user_id: str | None = None,
        title: str | None = None,
    ) -> Conversation:
        conv = Conversation(
            tenant_id=tenant_id,
            channel=channel,
            user_identifier=user_identifier,
            user_id=user_id,
            title=title,
            messages=[],
        )
        self._session.add(conv)
        self._session.flush()
        return conv

    def get_or_create(
        self,
        *,
        tenant_id: str,
        channel: str,
        user_identifier: str,
        user_id: str | None = None,
        title: str | None = None,
    ) -> Conversation:
        conv = self._session.scalar(
            select(Conversation).where(
                Conversation.tenant_id == tenant_id,
                Conversation.channel == channel,
                Conversation.user_identifier == user_identifier,
            )
        )
        if conv is not None:
            return conv
        conv = Conversation(
            tenant_id=tenant_id,
            channel=channel,
            user_identifier=user_identifier,
            user_id=user_id,
            title=title,
            messages=[],
        )
        self._session.add(conv)
        self._session.flush()
        return conv

    def append_messages(self, conversation: Conversation, new_messages: list[dict]) -> None:
        merged = list(conversation.messages or [])
        merged.extend(new_messages)
        conversation.messages = merged
        flag_modified(conversation, "messages")
        conversation.updated_at = datetime.now(timezone.utc)
        self._session.flush()

    def list_for_user(
        self, *, tenant_id: str, user_id: str, limit: int = 50
    ) -> list[Conversation]:
        return list(
            self._session.scalars(
                select(Conversation)
                .where(
                    Conversation.tenant_id == tenant_id,
                    Conversation.channel == "ui",
                    Conversation.user_id == user_id,
                )
                .order_by(desc(Conversation.updated_at))
                .limit(limit)
            ).all()
        )
