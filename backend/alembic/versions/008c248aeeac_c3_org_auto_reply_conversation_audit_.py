"""c3 org auto-reply + conversation audit + worker status

Revision ID: (auto)
Revises: (auto)
Create Date: (auto)
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "008c248aeeac"
down_revision = "0d3b851229d6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    # -----------------------------
    # 1) Org auto-reply toggle
    # -----------------------------
    # Assumes your org table is named "orgs" or "organizations".
    # We handle both safely.
    tables = set(insp.get_table_names())

    org_table = None
    if "orgs" in tables:
        org_table = "orgs"
    elif "organizations" in tables:
        org_table = "organizations"

    if org_table:
        cols = {c["name"] for c in insp.get_columns(org_table)}
        if "auto_reply_enabled" not in cols:
            op.add_column(
                org_table,
                sa.Column(
                    "auto_reply_enabled",
                    sa.Boolean(),
                    nullable=False,
                    server_default=sa.text("1"),
                ),
            )
            # Optional: remove server_default after backfill if you prefer
            # op.alter_column(org_table, "auto_reply_enabled", server_default=None)

    # -----------------------------
    # 2) Conversation audit log
    # -----------------------------
    if "conversation_audit" not in tables:
        op.create_table(
            "conversation_audit",
            sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),

            sa.Column("org_id", sa.BigInteger(), nullable=False, index=True),
            sa.Column("thread_key", sa.String(length=512), nullable=False, index=True),

            # who / what
            sa.Column("customer_email", sa.String(length=320), nullable=True, index=True),
            sa.Column("subject", sa.String(length=998), nullable=True),  # email subject max practical

            # IN = customer email, OUT = AI reply
            sa.Column("direction", sa.String(length=8), nullable=False),

            # raw content for audit
            sa.Column("body_text", sa.Text(), nullable=True),
            sa.Column("body_html", sa.Text(), nullable=True),

            # useful metadata
            sa.Column("email_message_id", sa.String(length=255), nullable=True, index=True),
            sa.Column("in_reply_to", sa.String(length=255), nullable=True),
            sa.Column("references", sa.Text(), nullable=True),

            # AI metadata (only for OUT usually)
            sa.Column("ai_model", sa.String(length=100), nullable=True),
            sa.Column("ai_tokens_in", sa.Integer(), nullable=True),
            sa.Column("ai_tokens_out", sa.Integer(), nullable=True),

            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
                index=True,
            ),
        )

        # Minimal integrity checks (soft, DB-agnostic)
        op.create_index(
            "ix_conversation_audit_org_thread_created",
            "conversation_audit",
            ["org_id", "thread_key", "created_at"],
        )

    # -----------------------------
    # 3) Worker health status (single row per worker_id)
    # -----------------------------
    if "worker_status" not in tables:
        op.create_table(
            "worker_status",
            sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),

            sa.Column("worker_id", sa.String(length=64), nullable=False, unique=True, index=True),

            sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("last_email_processed_at", sa.DateTime(timezone=True), nullable=True),

            sa.Column("last_email_message_id", sa.String(length=255), nullable=True),
            sa.Column("last_thread_key", sa.String(length=512), nullable=True),

            # quick health flags
            sa.Column("lock_health_ok", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("credits_health_ok", sa.Boolean(), nullable=False, server_default=sa.true()),


            # last seen error
            sa.Column("last_error", sa.Text(), nullable=True),

            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
        )


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    tables = set(insp.get_table_names())

    if "worker_status" in tables:
        op.drop_table("worker_status")

    if "conversation_audit" in tables:
        op.drop_index("ix_conversation_audit_org_thread_created", table_name="conversation_audit")
        op.drop_table("conversation_audit")

    org_table = None
    if "orgs" in tables:
        org_table = "orgs"
    elif "organizations" in tables:
        org_table = "organizations"

    if org_table:
        cols = {c["name"] for c in insp.get_columns(org_table)}
        if "auto_reply_enabled" in cols:
            op.drop_column(org_table, "auto_reply_enabled")
