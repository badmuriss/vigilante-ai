"""whatsapp_configs

Revision ID: 0002
Revises: 0001
Create Date: 2026-05-25

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

GUID_TYPE = postgresql.UUID(as_uuid=False).with_variant(sa.String(36), "sqlite")
JSON_TYPE = postgresql.JSONB().with_variant(sa.JSON(), "sqlite")


def upgrade() -> None:
    is_postgres = op.get_bind().dialect.name == "postgresql"
    false_default = sa.text("false" if is_postgres else "0")
    true_default = sa.text("true" if is_postgres else "1")
    json_array_default = sa.text("'[]'::jsonb" if is_postgres else "'[]'")

    op.create_table(
        "whatsapp_configs",
        sa.Column("id", GUID_TYPE, primary_key=True),
        sa.Column(
            "tenant_id",
            GUID_TYPE,
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("enabled", sa.Boolean, nullable=False, server_default=false_default),
        sa.Column("phone_number_id", sa.String(64), nullable=True),
        sa.Column("access_token_encrypted", sa.Text, nullable=True),
        sa.Column("template_name", sa.String(128), nullable=True),
        sa.Column(
            "template_language",
            sa.String(16),
            nullable=False,
            server_default="pt_BR",
        ),
        sa.Column(
            "recipients",
            JSON_TYPE,
            nullable=False,
            server_default=json_array_default,
        ),
        sa.Column(
            "include_image",
            sa.Boolean,
            nullable=False,
            server_default=true_default,
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


def downgrade() -> None:
    op.drop_table("whatsapp_configs")
