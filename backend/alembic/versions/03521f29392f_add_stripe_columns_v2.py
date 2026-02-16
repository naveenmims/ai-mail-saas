"""add_stripe_columns_v2

Revision ID: 03521f29392f
Revises: be5fb6f3ad01
Create Date: 2026-02-15 16:36:23.730539

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '03521f29392f'
down_revision: Union[str, Sequence[str], None] = 'be5fb6f3ad01'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None
from alembic import op


def upgrade():
    op.add_column("organizations", sa.Column("stripe_customer_id", sa.String(), nullable=True))
    op.add_column("organizations", sa.Column("stripe_subscription_id", sa.String(), nullable=True))
    op.add_column("organizations", sa.Column("stripe_price_id", sa.String(), nullable=True))
    op.add_column("organizations", sa.Column("subscription_status", sa.String(), server_default="inactive", nullable=False))

def downgrade():
    op.drop_column("organizations", "subscription_status")
    op.drop_column("organizations", "stripe_price_id")
    op.drop_column("organizations", "stripe_subscription_id")
    op.drop_column("organizations", "stripe_customer_id")
