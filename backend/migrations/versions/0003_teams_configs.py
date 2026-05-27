"""teams_configs

Revision ID: 0003
Revises: 0002
Create Date: 2026-05-27

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

GUID_TYPE = postgresql.UUID(as_uuid=False).with_variant(sa.String(36), "sqlite")


def upgrade() -> None:
    is_postgres = op.get_bind().dialect.name == "postgresql"
    false_default = sa.text("false" if is_postgres else "0")
    true_default = sa.text("true" if is_postgres else "1")

    op.create_table(
        "teams_configs",
        sa.Column("id", GUID_TYPE, primary_key=True),
        sa.Column(
            "tenant_id",
            GUID_TYPE,
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("enabled", sa.Boolean, nullable=False, server_default=false_default),
        sa.Column("webhook_url_encrypted", sa.Text, nullable=True),
        sa.Column("channel_name", sa.String(128), nullable=True),
        sa.Column(
            "notify_on_confirmed",
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
    op.drop_table("teams_configs")
