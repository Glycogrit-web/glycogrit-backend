"""Fix tier requires_payment consistency

Revision ID: fix_tier_payment
Revises: 20260428_activity_types
Create Date: 2026-04-28

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'fix_tier_payment'
down_revision = '20260428_activity_types'
branch_labels = None
depends_on = None


def upgrade():
    """
    Fix inconsistent requires_payment values in event_registration_tiers table.
    - If price = 0, set requires_payment = False
    - If price > 0, set requires_payment = True
    """
    # Update free tiers (price = 0) to not require payment
    op.execute("""
        UPDATE event_registration_tiers
        SET requires_payment = FALSE
        WHERE price = 0 AND requires_payment = TRUE
    """)

    # Update paid tiers (price > 0) to require payment
    op.execute("""
        UPDATE event_registration_tiers
        SET requires_payment = TRUE
        WHERE price > 0 AND requires_payment = FALSE
    """)


def downgrade():
    """
    No downgrade needed - this is a data consistency fix.
    The previous state was inconsistent and shouldn't be restored.
    """
    pass
