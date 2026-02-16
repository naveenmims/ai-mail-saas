"""add_stripe_fields_to_organizations

Revision ID: be5fb6f3ad01
Revises: 008c248aeeac
Create Date: 2026-02-15 16:31:46.066150

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'be5fb6f3ad01'
down_revision: Union[str, Sequence[str], None] = '008c248aeeac'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    from alembic import op
    import sqlalchemy as sa

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

    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
