"""add_shipping_address_to_registrations

Revision ID: 764f6e5cb521
Revises: 20260502_shiprocket
Create Date: 2026-05-03 04:13:57.357215

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '764f6e5cb521'
down_revision: Union[str, None] = '20260502_shiprocket'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add shipping address columns to registrations table
    op.add_column('registrations', sa.Column('shipping_address_line1', sa.String(255), nullable=True))
    op.add_column('registrations', sa.Column('shipping_address_line2', sa.String(255), nullable=True))
    op.add_column('registrations', sa.Column('shipping_city', sa.String(100), nullable=True))
    op.add_column('registrations', sa.Column('shipping_state', sa.String(100), nullable=True))
    op.add_column('registrations', sa.Column('shipping_postal_code', sa.String(20), nullable=True))
    op.add_column('registrations', sa.Column('shipping_country', sa.String(100), nullable=True, server_default='India'))
    op.add_column('registrations', sa.Column('shipping_phone', sa.String(20), nullable=True))
    op.add_column('registrations', sa.Column('shipping_email', sa.String(255), nullable=True))


def downgrade() -> None:
    # Remove shipping address columns from registrations table
    op.drop_column('registrations', 'shipping_email')
    op.drop_column('registrations', 'shipping_phone')
    op.drop_column('registrations', 'shipping_country')
    op.drop_column('registrations', 'shipping_postal_code')
    op.drop_column('registrations', 'shipping_state')
    op.drop_column('registrations', 'shipping_city')
    op.drop_column('registrations', 'shipping_address_line2')
    op.drop_column('registrations', 'shipping_address_line1')
