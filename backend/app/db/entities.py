"""ORM entities (Phase B schema).

Tables are scoped by `tenant_id` from day one even though Phase B is
single-tenant — this avoids a destructive migration when Phase C lands.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import CHAR, TypeDecorator

from app.db.base import Base


class GUID(TypeDecorator):
    """Store UUID strings as native UUID on Postgres and CHAR(36) elsewhere."""

    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):  # type: ignore[no-untyped-def]
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PG_UUID(as_uuid=False))
        return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value, dialect):  # type: ignore[no-untyped-def]
        if value is None:
            return None
        parsed = value if isinstance(value, uuid.UUID) else uuid.UUID(str(value))
        return str(parsed)

    def process_result_value(self, value, dialect):  # type: ignore[no-untyped-def]
        if value is None:
            return value
        return str(value)


JSON_TYPE = JSONB().with_variant(JSON(), "sqlite")


def _uuid() -> str:
    return str(uuid.uuid4())


class Tenant(Base):
    __tablename__ = "tenants"

    id: Mapped[str] = mapped_column(GUID(), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    users: Mapped[list["User"]] = relationship(back_populates="tenant")
    sites: Mapped[list["Site"]] = relationship(back_populates="tenant")
    whatsapp_config: Mapped["WhatsAppConfig | None"] = relationship(
        back_populates="tenant", cascade="all, delete-orphan", uselist=False
    )
    teams_config: Mapped["TeamsConfig | None"] = relationship(
        back_populates="tenant", cascade="all, delete-orphan", uselist=False
    )


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(GUID(), primary_key=True, default=_uuid)
    tenant_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    email: Mapped[str] = mapped_column(String(254), nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False, default="viewer")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    tenant: Mapped[Tenant] = relationship(back_populates="users")


class Site(Base):
    __tablename__ = "sites"

    id: Mapped[str] = mapped_column(GUID(), primary_key=True, default=_uuid)
    tenant_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    location: Mapped[str | None] = mapped_column(String(256), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    tenant: Mapped[Tenant] = relationship(back_populates="sites")
    cameras: Mapped[list["Camera"]] = relationship(back_populates="site")


class Camera(Base):
    __tablename__ = "cameras"

    id: Mapped[str] = mapped_column(GUID(), primary_key=True, default=_uuid)
    site_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("sites.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    source_kind: Mapped[str] = mapped_column(String(16), nullable=False)
    rtsp_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    local_index: Mapped[int | None] = mapped_column(Integer, nullable=True)
    location: Mapped[str | None] = mapped_column(String(256), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    last_seen_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    site: Mapped[Site] = relationship(back_populates="cameras")
    alerts: Mapped[list["Alert"]] = relationship(
        back_populates="camera", cascade="all, delete-orphan"
    )
    sessions: Mapped[list["Session"]] = relationship(
        back_populates="camera", cascade="all, delete-orphan"
    )


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[str] = mapped_column(GUID(), primary_key=True, default=_uuid)
    camera_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("cameras.id", ondelete="CASCADE"), nullable=False
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    violation_type: Mapped[str] = mapped_column(String(255), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    missing_epis: Mapped[list[str]] = mapped_column(JSON_TYPE, nullable=False, default=list)
    frame_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    thumbnail_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Raw (un-annotated) frame for retraining export. Annotated frame in
    # frame_path is for human review; YOLO training needs clean pixels.
    frame_raw_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Detections that triggered the alert: list of {class_name, bbox, confidence}.
    # Used to materialise YOLO labels when feedback exports happen.
    detected_bboxes: Mapped[list[dict] | None] = mapped_column(JSON_TYPE, nullable=True)
    # User feedback for online learning. NULL = pending review (soft alert),
    # "correct" = confirmed incident, "false_positive" = model was wrong.
    feedback: Mapped[str | None] = mapped_column(String(32), nullable=True)
    feedback_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    camera: Mapped[Camera] = relationship(back_populates="alerts")

    __table_args__ = (
        Index("ix_alerts_camera_timestamp", "camera_id", "timestamp"),
    )


class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(GUID(), primary_key=True, default=_uuid)
    camera_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("cameras.id", ondelete="CASCADE"), nullable=False
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    ended_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    camera: Mapped[Camera] = relationship(back_populates="sessions")
    total_frames: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    compliant_frames: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class WhatsAppConfig(Base):
    """Per-tenant WhatsApp Cloud API configuration.

    One row per tenant (`tenant_id` is UNIQUE). `access_token_encrypted`
    holds a Fernet-encrypted Meta access token — never stored in plain
    text. `recipients` is a JSON list of E.164 phone numbers (e.g.
    "+5511999999999"). Notifications fire only when `enabled=True` AND
    `recipients` is non-empty AND the row has a token + phone_number_id.
    """

    __tablename__ = "whatsapp_configs"

    id: Mapped[str] = mapped_column(GUID(), primary_key=True, default=_uuid)
    tenant_id: Mapped[str] = mapped_column(
        GUID(),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    phone_number_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    access_token_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    template_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    template_language: Mapped[str] = mapped_column(
        String(16), nullable=False, default="pt_BR"
    )
    recipients: Mapped[list[str]] = mapped_column(
        JSON_TYPE, nullable=False, default=list
    )
    include_image: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    # Conversational HUB (inbound webhook). Both encrypted with Fernet so the
    # row never holds plain-text Meta secrets. `phone_number_id` already exists
    # above; we add a unique index in migration 0004 so the webhook handler
    # can resolve tenant from the Meta payload.
    webhook_verify_token_encrypted: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )
    app_secret_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    tenant: Mapped[Tenant] = relationship(back_populates="whatsapp_config")


class Conversation(Base):
    """Stateless agent conversation, keyed by (tenant, channel, user_identifier).

    `channel` is `ui` (web chat) or `whatsapp` (inbound webhook). The agent
    history lives inline in `messages` as a JSON array of `{role, content, ...}`
    objects so a single SELECT loads the full thread. Multi-tenant by FK to
    `tenants`. `user_id` is set when the channel is `ui` (linked to the
    authenticated user) and NULL when the channel is `whatsapp`.
    """

    __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(GUID(), primary_key=True, default=_uuid)
    tenant_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    channel: Mapped[str] = mapped_column(String(16), nullable=False)
    user_identifier: Mapped[str] = mapped_column(String(128), nullable=False)
    user_id: Mapped[str | None] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    title: Mapped[str | None] = mapped_column(String(200), nullable=True)
    messages: Mapped[list[dict]] = mapped_column(
        JSON_TYPE, nullable=False, default=list
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    __table_args__ = (
        Index("ix_conversations_tenant_updated", "tenant_id", "updated_at"),
        Index(
            "ux_conversations_channel_user",
            "tenant_id",
            "channel",
            "user_identifier",
            unique=True,
        ),
    )


class KBDocument(Base):
    """Source document indexed in the RAG knowledge base.

    `tenant_id` NULL means "global" (visible to every tenant) — used for the
    seeded Vigilante.AI manual + NR-6/NR-18 excerpts. Tenant-uploaded docs
    have a concrete `tenant_id`. Idempotent on `(tenant_id, content_hash)`.
    """

    __tablename__ = "kb_documents"

    id: Mapped[str] = mapped_column(GUID(), primary_key=True, default=_uuid)
    tenant_id: Mapped[str | None] = mapped_column(
        GUID(), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True
    )
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    doc_metadata: Mapped[dict] = mapped_column(
        "metadata", JSON_TYPE, nullable=False, default=dict
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    chunks: Mapped[list["KBChunk"]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_kb_documents_tenant", "tenant_id"),
    )


class KBChunk(Base):
    """A retrievable slice of a `KBDocument` with embedding + FTS vector.

    `embedding` uses pgvector (1536-dim, OpenAI text-embedding-3-small).
    `tsv` is a generated Portuguese tsvector — created by the migration so
    SQLAlchemy doesn't try to materialise it on inserts.
    """

    __tablename__ = "kb_chunks"

    id: Mapped[str] = mapped_column(GUID(), primary_key=True, default=_uuid)
    tenant_id: Mapped[str | None] = mapped_column(
        GUID(), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True
    )
    document_id: Mapped[str] = mapped_column(
        GUID(),
        ForeignKey("kb_documents.id", ondelete="CASCADE"),
        nullable=False,
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    chunk_metadata: Mapped[dict] = mapped_column(
        "metadata", JSON_TYPE, nullable=False, default=dict
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    document: Mapped[KBDocument] = relationship(back_populates="chunks")

    # The vector column is declared in the migration (pgvector type) and
    # the tsvector column is generated. We access them through raw SQL in
    # `app/kb/retrieval.py` rather than via the ORM so the ORM model stays
    # backend-agnostic (sqlite for tests has neither column).


class TeamsConfig(Base):
    """Per-tenant Microsoft Teams webhook configuration.

    `webhook_url_encrypted` is a secret URL generated by Teams Workflows /
    Power Automate. Anyone with the URL can post to the target chat/channel,
    so it is encrypted at rest and never returned through the API.
    """

    __tablename__ = "teams_configs"

    id: Mapped[str] = mapped_column(GUID(), primary_key=True, default=_uuid)
    tenant_id: Mapped[str] = mapped_column(
        GUID(),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    webhook_url_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    channel_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    notify_on_confirmed: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    tenant: Mapped[Tenant] = relationship(back_populates="teams_config")
