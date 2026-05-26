"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-05-06

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

GUID_TYPE = postgresql.UUID(as_uuid=False).with_variant(sa.String(36), "sqlite")
JSON_TYPE = postgresql.JSONB().with_variant(sa.JSON(), "sqlite")


def _json_array_default() -> sa.TextClause:
    if op.get_bind().dialect.name == "postgresql":
        return sa.text("'[]'::jsonb")
    return sa.text("'[]'")

def upgrade() -> None:
    op.create_table(
        "tenants",
        sa.Column("id", GUID_TYPE, primary_key=True),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    op.create_table(
        "users",
        sa.Column("id", GUID_TYPE, primary_key=True),
        sa.Column(
            "tenant_id",
            GUID_TYPE,
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("email", sa.String(254), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("role", sa.String(32), nullable=False, server_default="viewer"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    op.create_table(
        "sites",
        sa.Column("id", GUID_TYPE, primary_key=True),
        sa.Column(
            "tenant_id",
            GUID_TYPE,
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("location", sa.String(256), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    op.create_table(
        "cameras",
        sa.Column("id", GUID_TYPE, primary_key=True),
        sa.Column(
            "site_id",
            GUID_TYPE,
            sa.ForeignKey("sites.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("source_kind", sa.String(16), nullable=False),
        sa.Column("rtsp_url", sa.Text, nullable=True),
        sa.Column("local_index", sa.Integer, nullable=True),
        sa.Column("location", sa.String(256), nullable=True),
        sa.Column("active", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    op.create_table(
        "alerts",
        sa.Column("id", GUID_TYPE, primary_key=True),
        sa.Column(
            "camera_id",
            GUID_TYPE,
            sa.ForeignKey("cameras.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "timestamp",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("violation_type", sa.String(255), nullable=False),
        sa.Column("confidence", sa.Float, nullable=False),
        sa.Column(
            "missing_epis",
            JSON_TYPE,
            nullable=False,
            server_default=_json_array_default(),
        ),
        sa.Column("frame_path", sa.Text, nullable=True),
        sa.Column("thumbnail_path", sa.Text, nullable=True),
    )
    op.create_index(
        "ix_alerts_camera_timestamp", "alerts", ["camera_id", "timestamp"]
    )

    op.create_table(
        "sessions",
        sa.Column("id", GUID_TYPE, primary_key=True),
        sa.Column(
            "camera_id",
            GUID_TYPE,
            sa.ForeignKey("cameras.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("total_frames", sa.Integer, nullable=False, server_default="0"),
        sa.Column("compliant_frames", sa.Integer, nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_table("sessions")
    op.drop_index("ix_alerts_camera_timestamp", table_name="alerts")
    op.drop_table("alerts")
    op.drop_table("cameras")
    op.drop_table("sites")
    op.drop_table("users")
    op.drop_table("tenants")
