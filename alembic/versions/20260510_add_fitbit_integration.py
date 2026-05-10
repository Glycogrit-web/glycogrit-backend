"""Add Fitbit integration tables

Revision ID: 20260510_add_fitbit_integration
Revises: 20260510_add_garmin_integration
Create Date: 2026-05-10

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20260510_add_fitbit_integration'
down_revision = '20260510_add_garmin_integration'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create fitbit_connections table"""
    op.create_table(
        'fitbit_connections',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('fitbit_user_id', sa.String(length=255), nullable=False),
        sa.Column('access_token', sa.Text(), nullable=False),
        sa.Column('refresh_token', sa.Text(), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('scope', sa.String(length=500), nullable=True),
        sa.Column('user_data', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('last_sync_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id'),
        sa.UniqueConstraint('fitbit_user_id')
    )

    # Create indexes for performance
    op.create_index('ix_fitbit_connections_id', 'fitbit_connections', ['id'])
    op.create_index('ix_fitbit_connections_user_id', 'fitbit_connections', ['user_id'])
    op.create_index('ix_fitbit_connections_fitbit_user_id', 'fitbit_connections', ['fitbit_user_id'])


def downgrade() -> None:
    """Drop fitbit_connections table"""
    op.drop_index('ix_fitbit_connections_fitbit_user_id', table_name='fitbit_connections')
    op.drop_index('ix_fitbit_connections_user_id', table_name='fitbit_connections')
    op.drop_index('ix_fitbit_connections_id', table_name='fitbit_connections')
    op.drop_table('fitbit_connections')
