"""conversational HUB (chat + RAG)

Revision ID: 0004
Revises: 0003
Create Date: 2026-05-27

Enables pgvector + adds tables for the conversational HUB:
- `conversations`           (per-tenant agent threads, channel-agnostic)
- `kb_documents`            (source docs, tenant-scoped or global)
- `kb_chunks`               (chunks with vector(1536) embedding + Portuguese tsvector)

Also extends `whatsapp_configs` with inbound-webhook credentials
(`webhook_verify_token_encrypted`, `app_secret_encrypted`) and a unique
index on `phone_number_id` so the webhook handler can resolve tenant.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

GUID_TYPE = postgresql.UUID(as_uuid=False).with_variant(sa.String(36), "sqlite")
JSON_TYPE = postgresql.JSONB().with_variant(sa.JSON(), "sqlite")


def upgrade() -> None:
    bind = op.get_bind()
    is_postgres = bind.dialect.name == "postgresql"

    if is_postgres:
        # pgvector for embeddings, pg_trgm for fuzzy fallback.
        op.execute("CREATE EXTENSION IF NOT EXISTS vector")
        op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    # --- whatsapp_configs extension -----------------------------------------
    op.add_column(
        "whatsapp_configs",
        sa.Column("webhook_verify_token_encrypted", sa.Text, nullable=True),
    )
    op.add_column(
        "whatsapp_configs",
        sa.Column("app_secret_encrypted", sa.Text, nullable=True),
    )
    op.create_index(
        "ux_whatsapp_configs_phone_number_id",
        "whatsapp_configs",
        ["phone_number_id"],
        unique=True,
    )

    # --- conversations ------------------------------------------------------
    op.create_table(
        "conversations",
        sa.Column("id", GUID_TYPE, primary_key=True),
        sa.Column(
            "tenant_id",
            GUID_TYPE,
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("channel", sa.String(16), nullable=False),
        sa.Column("user_identifier", sa.String(128), nullable=False),
        sa.Column(
            "user_id",
            GUID_TYPE,
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("title", sa.String(200), nullable=True),
        sa.Column(
            "messages",
            JSON_TYPE,
            nullable=False,
            server_default=sa.text("'[]'::jsonb" if is_postgres else "'[]'"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_conversations_tenant_updated",
        "conversations",
        ["tenant_id", "updated_at"],
    )
    op.create_index(
        "ux_conversations_channel_user",
        "conversations",
        ["tenant_id", "channel", "user_identifier"],
        unique=True,
    )

    # --- kb_documents -------------------------------------------------------
    op.create_table(
        "kb_documents",
        sa.Column("id", GUID_TYPE, primary_key=True),
        sa.Column(
            "tenant_id",
            GUID_TYPE,
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("title", sa.String(256), nullable=False),
        sa.Column("source", sa.String(64), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column(
            "metadata",
            JSON_TYPE,
            nullable=False,
            server_default=sa.text("'{}'::jsonb" if is_postgres else "'{}'"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_kb_documents_tenant", "kb_documents", ["tenant_id"])
    # Unique by (tenant_id, content_hash); global docs (tenant_id NULL) get a
    # separate unique constraint on content_hash via partial index below.
    if is_postgres:
        op.create_index(
            "ux_kb_documents_hash_tenant",
            "kb_documents",
            ["tenant_id", "content_hash"],
            unique=True,
            postgresql_where=sa.text("tenant_id IS NOT NULL"),
        )
        op.create_index(
            "ux_kb_documents_hash_global",
            "kb_documents",
            ["content_hash"],
            unique=True,
            postgresql_where=sa.text("tenant_id IS NULL"),
        )
    else:
        op.create_index(
            "ux_kb_documents_hash_tenant",
            "kb_documents",
            ["tenant_id", "content_hash"],
            unique=True,
        )

    # --- kb_chunks ----------------------------------------------------------
    if is_postgres:
        op.execute(
            """
            CREATE TABLE kb_chunks (
                id UUID PRIMARY KEY,
                tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
                document_id UUID NOT NULL REFERENCES kb_documents(id) ON DELETE CASCADE,
                chunk_index INTEGER NOT NULL,
                content TEXT NOT NULL,
                embedding vector(1536),
                metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
                tsv tsvector GENERATED ALWAYS AS (to_tsvector('portuguese', content)) STORED,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """
        )
        op.execute("CREATE INDEX ix_kb_chunks_tenant_doc ON kb_chunks(tenant_id, document_id)")
        op.execute("CREATE INDEX ix_kb_chunks_tsv ON kb_chunks USING GIN (tsv)")
        op.execute(
            "CREATE INDEX ix_kb_chunks_embedding ON kb_chunks "
            "USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)"
        )
        op.execute(
            "CREATE UNIQUE INDEX ux_kb_chunks_doc_idx ON kb_chunks(document_id, chunk_index)"
        )
    else:
        # SQLite path (tests): no embedding, no tsvector. Search falls back
        # to LIKE in retrieval.py when the columns are absent.
        op.create_table(
            "kb_chunks",
            sa.Column("id", GUID_TYPE, primary_key=True),
            sa.Column(
                "tenant_id",
                GUID_TYPE,
                sa.ForeignKey("tenants.id", ondelete="CASCADE"),
                nullable=True,
            ),
            sa.Column(
                "document_id",
                GUID_TYPE,
                sa.ForeignKey("kb_documents.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("chunk_index", sa.Integer, nullable=False),
            sa.Column("content", sa.Text, nullable=False),
            sa.Column(
                "metadata",
                JSON_TYPE,
                nullable=False,
                server_default=sa.text("'{}'"),
            ),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
        )
        op.create_index(
            "ux_kb_chunks_doc_idx",
            "kb_chunks",
            ["document_id", "chunk_index"],
            unique=True,
        )


def downgrade() -> None:
    bind = op.get_bind()
    is_postgres = bind.dialect.name == "postgresql"

    op.drop_table("kb_chunks")
    op.drop_index("ix_kb_documents_tenant", table_name="kb_documents")
    op.drop_index("ux_kb_documents_hash_tenant", table_name="kb_documents")
    if is_postgres:
        op.drop_index("ux_kb_documents_hash_global", table_name="kb_documents")
    op.drop_table("kb_documents")
    op.drop_index("ix_conversations_tenant_updated", table_name="conversations")
    op.drop_index("ux_conversations_channel_user", table_name="conversations")
    op.drop_table("conversations")

    op.drop_index("ux_whatsapp_configs_phone_number_id", table_name="whatsapp_configs")
    op.drop_column("whatsapp_configs", "app_secret_encrypted")
    op.drop_column("whatsapp_configs", "webhook_verify_token_encrypted")
