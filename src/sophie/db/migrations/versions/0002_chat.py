"""add chat feature: user_config.llm_chat_provider + chat_message table

Revision ID: 0002
Revises: 0001
Create Date: 2026-08-16 22:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "user_config",
        sa.Column(
            "llm_chat_provider", sa.String(length=20), nullable=False, server_default="anthropic"
        ),
    )
    op.create_table(
        "chat_message",
        sa.Column("profile_id", sa.String(), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("provider", sa.String(length=20), nullable=True),
        sa.Column("content", sa.String(), nullable=False),
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["profile_id"],
            ["profile.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_chat_message_profile_id"), "chat_message", ["profile_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_chat_message_profile_id"), table_name="chat_message")
    op.drop_table("chat_message")
    op.drop_column("user_config", "llm_chat_provider")
