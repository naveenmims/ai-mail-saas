"""add thread reply locks

Revision ID: 0d3b851229d6
Revises: 22ce819db199
Create Date: 2026-02-15 00:06:01.908469

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table(
        "reply_thread_locks",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("org_id", sa.BigInteger(), nullable=False),
        sa.Column("thread_key", sa.String(length=255), nullable=False),
        # bucket_start = start timestamp of the cooldown bucket (e.g., 10-min bucket)
        sa.Column("bucket_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("worker_id", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
    )

    # Atomic protection: only ONE row per org+thread+bucket
    op.create_unique_constraint(
        "uq_reply_thread_locks_org_thread_bucket",
        "reply_thread_locks",
        ["org_id", "thread_key", "bucket_start"],
    )

    op.create_index(
        "ix_reply_thread_locks_expires_at",
        "reply_thread_locks",
        ["expires_at"],
    )


def downgrade():
    op.drop_index("ix_reply_thread_locks_expires_at", table_name="reply_thread_locks")
    op.drop_constraint("uq_reply_thread_locks_org_thread_bucket", "reply_thread_locks", type_="unique")
    op.drop_table("reply_thread_locks")


# revision identifiers, used by Alembic.
revision: str = '0d3b851229d6'
down_revision: Union[str, Sequence[str], None] = '22ce819db199'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
