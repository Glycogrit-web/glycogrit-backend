"""initial tables

Revision ID: 001
Revises:
Create Date: 2026-04-16 01:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('phone', sa.String(length=20), nullable=True),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('first_name', sa.String(length=100), nullable=False),
        sa.Column('last_name', sa.String(length=100), nullable=False),
        sa.Column('date_of_birth', sa.Date(), nullable=True),
        sa.Column('gender', sa.String(length=20), nullable=True),
        sa.Column('city', sa.String(length=100), nullable=True),
        sa.Column('state', sa.String(length=100), nullable=True),
        sa.Column('country', sa.String(length=100), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('email_verified', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_users_email', 'users', ['email'], unique=True)
    op.create_index('ix_users_phone', 'users', ['phone'], unique=True)
    op.create_index('ix_users_city', 'users', ['city'])
    op.create_index('ix_users_state', 'users', ['state'])

    # Create events table
    op.create_table(
        'events',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('slug', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('event_type', sa.String(length=50), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='draft'),
        sa.Column('event_date', sa.TIMESTAMP(), nullable=False),
        sa.Column('registration_start_date', sa.TIMESTAMP(), nullable=False),
        sa.Column('registration_end_date', sa.TIMESTAMP(), nullable=False),
        sa.Column('location_name', sa.String(length=255), nullable=False),
        sa.Column('city', sa.String(length=100), nullable=False),
        sa.Column('state', sa.String(length=100), nullable=False),
        sa.Column('country', sa.String(length=100), nullable=False),
        sa.Column('total_distance', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('max_participants', sa.Integer(), nullable=True),
        sa.Column('current_participants', sa.Integer(), server_default='0'),
        sa.Column('registration_fee', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('currency', sa.String(length=10), server_default='INR'),
        sa.Column('organizer_id', sa.Integer(), nullable=False),
        sa.Column('is_virtual', sa.Boolean(), server_default='false'),
        sa.Column('is_featured', sa.Boolean(), server_default='false'),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['organizer_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_events_slug', 'events', ['slug'], unique=True)
    op.create_index('ix_events_event_type', 'events', ['event_type'])
    op.create_index('ix_events_status', 'events', ['status'])
    op.create_index('ix_events_event_date', 'events', ['event_date'])
    op.create_index('ix_events_city', 'events', ['city'])
    op.create_index('ix_events_state', 'events', ['state'])
    op.create_index('ix_events_country', 'events', ['country'])
    op.create_index('ix_events_organizer_id', 'events', ['organizer_id'])

    # Create event_categories table
    op.create_table(
        'event_categories',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('event_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('distance', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('description', sa.String(length=255), nullable=True),
        sa.Column('max_participants', sa.Integer(), nullable=True),
        sa.Column('current_participants', sa.Integer(), server_default='0'),
        sa.Column('registration_fee', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['event_id'], ['events.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_event_categories_event_id', 'event_categories', ['event_id'])

    # Create registrations table
    op.create_table(
        'registrations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('event_id', sa.Integer(), nullable=False),
        sa.Column('event_category_id', sa.Integer(), nullable=True),
        sa.Column('registration_number', sa.String(length=50), nullable=False),
        sa.Column('bib_number', sa.String(length=50), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='pending'),
        sa.Column('participant_name', sa.String(length=255), nullable=False),
        sa.Column('age', sa.Integer(), nullable=True),
        sa.Column('gender', sa.String(length=20), nullable=True),
        sa.Column('t_shirt_size', sa.String(length=10), nullable=True),
        sa.Column('registered_at', sa.TIMESTAMP(), server_default=sa.text('now()'), nullable=False),
        sa.Column('confirmed_at', sa.TIMESTAMP(), nullable=True),
        sa.ForeignKeyConstraint(['event_category_id'], ['event_categories.id'], ),
        sa.ForeignKeyConstraint(['event_id'], ['events.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_registrations_user_id', 'registrations', ['user_id'])
    op.create_index('ix_registrations_event_id', 'registrations', ['event_id'])
    op.create_index('ix_registrations_event_category_id', 'registrations', ['event_category_id'])
    op.create_index('ix_registrations_registration_number', 'registrations', ['registration_number'], unique=True)
    op.create_index('ix_registrations_bib_number', 'registrations', ['bib_number'], unique=True)
    op.create_index('ix_registrations_status', 'registrations', ['status'])
    op.create_index('ix_registrations_registered_at', 'registrations', ['registered_at'])

    # Create payments table
    op.create_table(
        'payments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('registration_id', sa.Integer(), nullable=False),
        sa.Column('amount', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('currency', sa.String(length=10), server_default='INR'),
        sa.Column('payment_method', sa.String(length=50), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='pending'),
        sa.Column('transaction_id', sa.String(length=100), nullable=True),
        sa.Column('gateway_reference', sa.String(length=100), nullable=True),
        sa.Column('gateway_name', sa.String(length=50), nullable=True),
        sa.Column('initiated_at', sa.TIMESTAMP(), server_default=sa.text('now()'), nullable=False),
        sa.Column('completed_at', sa.TIMESTAMP(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['registration_id'], ['registrations.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_payments_user_id', 'payments', ['user_id'])
    op.create_index('ix_payments_registration_id', 'payments', ['registration_id'])
    op.create_index('ix_payments_status', 'payments', ['status'])
    op.create_index('ix_payments_transaction_id', 'payments', ['transaction_id'], unique=True)


def downgrade() -> None:
    op.drop_table('payments')
    op.drop_table('registrations')
    op.drop_table('event_categories')
    op.drop_table('events')
    op.drop_table('users')
