"""baseline

Revision ID: 776d86c2544a
Revises: 
Create Date: 2026-02-14

"""
from alembic import op  # noqa: F401
import sqlalchemy as sa  # noqa: F401

# revision identifiers, used by Alembic.
revision = "776d86c2544a"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # baseline stamp only — no schema changes
    pass


def downgrade():
    # baseline stamp only — no schema changes
    pass
