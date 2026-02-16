"""create core tables

Revision ID: 567de561759d
Revises: None
"""

revision = "567de561759d"
down_revision = None
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "567de561759d"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- organizations ---
    op.create_table(
        "organizations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=200), nullable=False),

        sa.Column("support_name", sa.Text(), nullable=True),
        sa.Column("support_email", sa.Text(), nullable=True),
        sa.Column("website", sa.Text(), nullable=True),
        sa.Column("kb_text", sa.Text(), nullable=True),
        sa.Column("system_prompt", sa.Text(), nullable=True),

        sa.Column("auto_reply", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("max_replies_per_hour", sa.Integer(), nullable=False, server_default="10"),
        sa.Column("cooldown_hours", sa.Integer(), nullable=False, server_default="24"),
        sa.Column("auto_reply_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
    )

    # --- users ---
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "org_id",
            sa.Integer(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("email", sa.String(length=255), nullable=False, unique=True),
        sa.Column("password", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=50), nullable=False, server_default="owner"),
    )
    op.create_index("ix_users_org_id", "users", ["org_id"])
    op.create_index("ix_users_email", "users", ["email"])

    # --- email_accounts ---
    op.create_table(
        "email_accounts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "org_id",
            sa.Integer(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),

        sa.Column("label", sa.String(length=100), nullable=False, server_default="Primary"),
        sa.Column("email", sa.String(length=255), nullable=False),

        sa.Column("imap_host", sa.String(length=255), nullable=False),
        sa.Column("imap_port", sa.Integer(), nullable=False, server_default="993"),
        sa.Column("imap_username", sa.String(length=255), nullable=False),
        sa.Column("imap_password", sa.String(length=255), nullable=False),

        sa.Column("sendgrid_api_key", sa.String(length=255), nullable=False),
        sa.Column("from_name", sa.String(length=255), nullable=False, server_default="AI Mail SaaS"),
    )
    op.create_index("ix_email_accounts_org_id", "email_accounts", ["org_id"])
    op.create_index("ix_email_accounts_email", "email_accounts", ["email"])


def downgrade() -> None:
    op.drop_index("ix_email_accounts_email", table_name="email_accounts")
    op.drop_index("ix_email_accounts_org_id", table_name="email_accounts")
    op.drop_table("email_accounts")

    op.drop_index("ix_users_email", table_name="users")
    op.drop_index("ix_users_org_id", table_name="users")
    op.drop_table("users")

    op.drop_table("organizations")
