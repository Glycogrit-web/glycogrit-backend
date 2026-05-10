"""Add Garmin integration tables

Revision ID: 20260510_add_garmin_integration
Revises: 20260510_remove_challenge_activities
Create Date: 2026-05-10

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20260510_add_garmin_integration'
down_revision = 'e9670aec43c7'  # Points to add_highest_wins_tracking
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create garmin_connections table"""
    op.create_table(
        'garmin_connections',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('access_token', sa.String(length=512), nullable=False),
        sa.Column('access_token_secret', sa.String(length=512), nullable=False),
        sa.Column('user_id_garmin', sa.String(length=255), nullable=False),
        sa.Column('user_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('last_sync_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id'),
        sa.UniqueConstraint('user_id_garmin')
    )

    # Create indexes for performance
    op.create_index('ix_garmin_connections_user_id', 'garmin_connections', ['user_id'])
    op.create_index('ix_garmin_connections_user_id_garmin', 'garmin_connections', ['user_id_garmin'])


def downgrade() -> None:
    """Drop garmin_connections table"""
    op.drop_index('ix_garmin_connections_user_id_garmin', table_name='garmin_connections')
    op.drop_index('ix_garmin_connections_user_id', table_name='garmin_connections')
    op.drop_table('garmin_connections')
