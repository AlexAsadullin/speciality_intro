"""initial

Revision ID: 0001
Revises:
Create Date: 2026-04-28

"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("username", sa.String(64), nullable=False, unique=True),
        sa.Column("email", sa.String(256), nullable=False, unique=True),
        sa.Column("hashed_password", sa.String(256), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("refresh_token", sa.String(512), nullable=True),
    )

    op.create_table(
        "user_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("source", sa.String(32), nullable=False),
        sa.Column("endpoint", sa.String(64), nullable=False),
        sa.Column("rows_downloaded", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("parameters", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.create_index("ix_user_requests_user_id", "user_requests", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_user_requests_user_id", table_name="user_requests")
    op.drop_table("user_requests")
    op.drop_table("users")
