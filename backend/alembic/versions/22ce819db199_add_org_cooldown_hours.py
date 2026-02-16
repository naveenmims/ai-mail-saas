"""add org cooldown_hours

Revision ID: 22ce819db199
Revises: 776d86c2544a
Create Date: 2026-02-14 23:06:09.561369

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '22ce819db199'
down_revision: Union[str, Sequence[str], None] = '776d86c2544a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision = "22ce819db199"
down_revision = "776d86c2544a"
branch_labels = None
depends_on = None


def _column_exists(bind, table_name: str, column_name: str) -> bool:
    q = text("""
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = :t
          AND column_name = :c
        LIMIT 1
    """)
    return bind.execute(q, {"t": table_name, "c": column_name}).fetchone() is not None


def upgrade() -> None:
    bind = op.get_bind()

    # If table doesn't exist yet, skip safely
    table_ok = bind.execute(
        text("""
            SELECT 1
            FROM information_schema.tables
            WHERE table_name = 'organizations'
            LIMIT 1
        """)
    ).fetchone()

    if not table_ok:
        return

    # Add only if missing
    if not _column_exists(bind, "organizations", "cooldown_hours"):
        op.add_column(
            "organizations",
            sa.Column("cooldown_hours", sa.Integer(), nullable=False, server_default="24"),
        )


def downgrade() -> None:
    bind = op.get_bind()
    table_ok = bind.execute(
        text("""
            SELECT 1
            FROM information_schema.tables
            WHERE table_name = 'organizations'
            LIMIT 1
        """)
    ).fetchone()

    if not table_ok:
        return

    if _column_exists(bind, "organizations", "cooldown_hours"):
        op.drop_column("organizations", "cooldown_hours")
    

def downgrade() -> None:
    # SQLite may error if column doesn't exist; make downgrade idempotent-ish
    bind = op.get_bind()
    cols = [r[1] for r in bind.exec_driver_sql("PRAGMA table_info(organizations)").fetchall()]
    if "cooldown_hours" in cols:
        op.drop_column("organizations", "cooldown_hours")
