"""Add multi-tier registration system

Revision ID: 20260427_multi_tier
Revises: 20260425_goodie_unlock
Create Date: 2026-04-27

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20260427_multi_tier'
down_revision = '20260425_goodie_unlock'
branch_labels = None
depends_on = None


def upgrade():
    # Create event_registration_tiers table
    op.create_table(
        'event_registration_tiers',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('event_id', sa.Integer(), nullable=False),
        sa.Column('tier_name', sa.String(length=100), nullable=False),
        sa.Column('tier_slug', sa.String(length=100), nullable=False),
        sa.Column('tier_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('price', sa.Numeric(precision=10, scale=2), nullable=False, server_default='0.00'),
        sa.Column('currency', sa.String(length=10), nullable=False, server_default='INR'),
        sa.Column('requires_payment', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('max_registrations', sa.Integer(), nullable=True),
        sa.Column('current_registrations', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('rewards', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes for event_registration_tiers
    op.create_index('idx_event_registration_tiers_event_id', 'event_registration_tiers', ['event_id'], unique=False)
    op.create_index('idx_event_registration_tiers_tier_slug', 'event_registration_tiers', ['tier_slug'], unique=False)
    op.create_index('idx_event_registration_tiers_is_active', 'event_registration_tiers', ['is_active'], unique=False)

    # Create unique constraints for event_registration_tiers
    op.create_unique_constraint('uq_event_tier_slug', 'event_registration_tiers', ['event_id', 'tier_slug'])
    op.create_unique_constraint('uq_event_tier_order', 'event_registration_tiers', ['event_id', 'tier_order'])

    # Create foreign key for event_registration_tiers
    op.create_foreign_key('fk_event_registration_tiers_event', 'event_registration_tiers', 'events', ['event_id'], ['id'], ondelete='CASCADE')

    # Create registration_tiers junction table
    op.create_table(
        'registration_tiers',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('registration_id', sa.Integer(), nullable=False),
        sa.Column('tier_id', sa.Integer(), nullable=False),
        sa.Column('registered_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('is_upgrade', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('upgraded_from_tier_id', sa.Integer(), nullable=True),
        sa.Column('upgrade_payment_id', sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes for registration_tiers
    op.create_index('idx_registration_tiers_registration_id', 'registration_tiers', ['registration_id'], unique=False)
    op.create_index('idx_registration_tiers_tier_id', 'registration_tiers', ['tier_id'], unique=False)

    # Create unique constraint for registration_tiers
    op.create_unique_constraint('uq_registration_tier', 'registration_tiers', ['registration_id', 'tier_id'])

    # Create foreign keys for registration_tiers
    op.create_foreign_key('fk_registration_tiers_registration', 'registration_tiers', 'registrations', ['registration_id'], ['id'], ondelete='CASCADE')
    op.create_foreign_key('fk_registration_tiers_tier', 'registration_tiers', 'event_registration_tiers', ['tier_id'], ['id'])
    op.create_foreign_key('fk_registration_tiers_upgraded_from', 'registration_tiers', 'event_registration_tiers', ['upgraded_from_tier_id'], ['id'])
    op.create_foreign_key('fk_registration_tiers_upgrade_payment', 'registration_tiers', 'payments', ['upgrade_payment_id'], ['id'])

    # Add columns to events table
    op.add_column('events', sa.Column('uses_tier_system', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('events', sa.Column('default_tier_id', sa.Integer(), nullable=True))

    # Create index and foreign key for events.default_tier_id
    op.create_index('idx_events_default_tier_id', 'events', ['default_tier_id'], unique=False)
    op.create_foreign_key('fk_events_default_tier', 'events', 'event_registration_tiers', ['default_tier_id'], ['id'])

    # Add columns to registrations table
    op.add_column('registrations', sa.Column('current_tier_id', sa.Integer(), nullable=True))
    op.add_column('registrations', sa.Column('uses_tier_system', sa.Boolean(), nullable=False, server_default='false'))

    # Create index and foreign key for registrations.current_tier_id
    op.create_index('idx_registrations_current_tier_id', 'registrations', ['current_tier_id'], unique=False)
    op.create_foreign_key('fk_registrations_current_tier', 'registrations', 'event_registration_tiers', ['current_tier_id'], ['id'])

    # Add columns to payments table
    op.add_column('payments', sa.Column('tier_id', sa.Integer(), nullable=True))
    op.add_column('payments', sa.Column('is_tier_upgrade', sa.Boolean(), nullable=False, server_default='false'))

    # Create index and foreign key for payments.tier_id
    op.create_index('idx_payments_tier_id', 'payments', ['tier_id'], unique=False)
    op.create_foreign_key('fk_payments_tier', 'payments', 'event_registration_tiers', ['tier_id'], ['id'])


def downgrade():
    # Drop foreign keys and indexes from payments
    op.drop_constraint('fk_payments_tier', 'payments', type_='foreignkey')
    op.drop_index('idx_payments_tier_id', table_name='payments')
    op.drop_column('payments', 'is_tier_upgrade')
    op.drop_column('payments', 'tier_id')

    # Drop foreign keys and indexes from registrations
    op.drop_constraint('fk_registrations_current_tier', 'registrations', type_='foreignkey')
    op.drop_index('idx_registrations_current_tier_id', table_name='registrations')
    op.drop_column('registrations', 'uses_tier_system')
    op.drop_column('registrations', 'current_tier_id')

    # Drop foreign keys and indexes from events
    op.drop_constraint('fk_events_default_tier', 'events', type_='foreignkey')
    op.drop_index('idx_events_default_tier_id', table_name='events')
    op.drop_column('events', 'default_tier_id')
    op.drop_column('events', 'uses_tier_system')

    # Drop registration_tiers table
    op.drop_constraint('fk_registration_tiers_upgrade_payment', 'registration_tiers', type_='foreignkey')
    op.drop_constraint('fk_registration_tiers_upgraded_from', 'registration_tiers', type_='foreignkey')
    op.drop_constraint('fk_registration_tiers_tier', 'registration_tiers', type_='foreignkey')
    op.drop_constraint('fk_registration_tiers_registration', 'registration_tiers', type_='foreignkey')
    op.drop_constraint('uq_registration_tier', 'registration_tiers', type_='unique')
    op.drop_index('idx_registration_tiers_tier_id', table_name='registration_tiers')
    op.drop_index('idx_registration_tiers_registration_id', table_name='registration_tiers')
    op.drop_table('registration_tiers')

    # Drop event_registration_tiers table
    op.drop_constraint('fk_event_registration_tiers_event', 'event_registration_tiers', type_='foreignkey')
    op.drop_constraint('uq_event_tier_order', 'event_registration_tiers', type_='unique')
    op.drop_constraint('uq_event_tier_slug', 'event_registration_tiers', type_='unique')
    op.drop_index('idx_event_registration_tiers_is_active', table_name='event_registration_tiers')
    op.drop_index('idx_event_registration_tiers_tier_slug', table_name='event_registration_tiers')
    op.drop_index('idx_event_registration_tiers_event_id', table_name='event_registration_tiers')
    op.drop_table('event_registration_tiers')
