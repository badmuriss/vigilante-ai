"""whatsapp operators + global creds

Revision ID: 0005
Revises: 0004
Create Date: 2026-05-28

The single shared platform WhatsApp number means Meta credentials are now
global (env/settings), not per-tenant. This migration:

- creates `whatsapp_operators` (phone UNIQUE globally -> operator belongs to
  exactly one tenant; the inbound webhook resolves tenant from `msg.from`).
- drops the now-global credential columns from `whatsapp_configs` and the
  unique index on `phone_number_id`. Operators start empty (existing
  `recipients` are NOT migrated, per product decision).
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

GUID_TYPE = postgresql.UUID(as_uuid=False).with_variant(sa.String(36), "sqlite")
JSON_TYPE = postgresql.JSONB().with_variant(sa.JSON(), "sqlite")

_DROPPED_COLS = [
    "phone_number_id",
    "access_token_encrypted",
    "template_name",
    "template_language",
    "recipients",
    "webhook_verify_token_encrypted",
    "app_secret_encrypted",
]


def upgrade() -> None:
    op.create_table(
        "whatsapp_operators",
        sa.Column("id", GUID_TYPE, primary_key=True),
        sa.Column(
            "tenant_id",
            GUID_TYPE,
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("phone", sa.String(20), nullable=False),
        sa.Column("name", sa.String(120), nullable=True),
        sa.Column(
            "enabled", sa.Boolean, nullable=False, server_default=sa.text("true")
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
        "ux_whatsapp_operators_phone", "whatsapp_operators", ["phone"], unique=True
    )
    op.create_index(
        "ix_whatsapp_operators_tenant", "whatsapp_operators", ["tenant_id"]
    )

    op.drop_index(
        "ux_whatsapp_configs_phone_number_id", table_name="whatsapp_configs"
    )
    with op.batch_alter_table("whatsapp_configs") as batch:
        for col in _DROPPED_COLS:
            batch.drop_column(col)


def downgrade() -> None:
    with op.batch_alter_table("whatsapp_configs") as batch:
        batch.add_column(sa.Column("phone_number_id", sa.String(64), nullable=True))
        batch.add_column(
            sa.Column("access_token_encrypted", sa.Text, nullable=True)
        )
        batch.add_column(sa.Column("template_name", sa.String(128), nullable=True))
        batch.add_column(
            sa.Column(
                "template_language",
                sa.String(16),
                nullable=False,
                server_default="pt_BR",
            )
        )
        batch.add_column(
            sa.Column(
                "recipients",
                JSON_TYPE,
                nullable=False,
                server_default=sa.text("'[]'"),
            )
        )
        batch.add_column(
            sa.Column("webhook_verify_token_encrypted", sa.Text, nullable=True)
        )
        batch.add_column(
            sa.Column("app_secret_encrypted", sa.Text, nullable=True)
        )
    op.create_index(
        "ux_whatsapp_configs_phone_number_id",
        "whatsapp_configs",
        ["phone_number_id"],
        unique=True,
    )

    op.drop_index("ix_whatsapp_operators_tenant", table_name="whatsapp_operators")
    op.drop_index("ux_whatsapp_operators_phone", table_name="whatsapp_operators")
    op.drop_table("whatsapp_operators")
