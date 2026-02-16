"""merge heads

Revision ID: cc229af53430
Revises: 03521f29392f, 567de561759d
Create Date: 2026-02-16 10:28:14.149603

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cc229af53430'
down_revision: Union[str, Sequence[str], None] = ('03521f29392f', '567de561759d')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
