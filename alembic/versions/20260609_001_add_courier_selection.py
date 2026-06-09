"""Add courier selection fields

Revision ID: 20260609_001_courier_selection
Revises: 64cec31dd3a1
Create Date: 2026-06-09 12:00:00.000000

"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "20260609_001_courier_selection"
down_revision: str | None = "64cec31dd3a1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add courier selection and auto-selection fields"""

    # Add columns to shiprocket_config table
    op.add_column(
        'shiprocket_config',
        sa.Column('courier_selection_strategy', sa.String(50), nullable=False, server_default='cheapest')
    )
    op.add_column(
        'shiprocket_config',
        sa.Column('auto_select_courier', sa.Boolean(), nullable=False, server_default='true')
    )
    op.add_column(
        'shiprocket_config',
        sa.Column('blacklisted_couriers', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]')
    )

    # Add columns to shiprocket_orders table
    op.add_column(
        'shiprocket_orders',
        sa.Column('selected_courier_rate', sa.Numeric(10, 2), nullable=True)
    )
    op.add_column(
        'shiprocket_orders',
        sa.Column('alternative_couriers', postgresql.JSONB(astext_type=sa.Text()), nullable=True)
    )
    op.add_column(
        'shiprocket_orders',
        sa.Column('cost_savings', sa.Numeric(10, 2), nullable=True)
    )
    op.add_column(
        'shiprocket_orders',
        sa.Column('selection_strategy_used', sa.String(50), nullable=True)
    )
    op.add_column(
        'shiprocket_orders',
        sa.Column('last_courier_reassignment_at', sa.DateTime(timezone=True), nullable=True)
    )


def downgrade() -> None:
    """Remove courier selection fields"""

    # Remove columns from shiprocket_orders table
    op.drop_column('shiprocket_orders', 'last_courier_reassignment_at')
    op.drop_column('shiprocket_orders', 'selection_strategy_used')
    op.drop_column('shiprocket_orders', 'cost_savings')
    op.drop_column('shiprocket_orders', 'alternative_couriers')
    op.drop_column('shiprocket_orders', 'selected_courier_rate')

    # Remove columns from shiprocket_config table
    op.drop_column('shiprocket_config', 'blacklisted_couriers')
    op.drop_column('shiprocket_config', 'auto_select_courier')
    op.drop_column('shiprocket_config', 'courier_selection_strategy')
