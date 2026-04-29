"""refactor_activity_structure_for_registration

Revision ID: 3451509c9ce5
Revises: add_payment_tracking
Create Date: 2026-04-30 03:50:20.163451

Major refactoring to clarify activity structure:
1. Rename event_categories → event_activities (represents selectable activities like "5K Run", "10K Cycle")
2. Rename event_activities → user_activity_logs (tracks daily user activity submissions)
3. Add activity_type column to event_activities (new name)
4. Add event_activity_id to registrations table
5. Remove event_type from events table
6. Drop event_activity_types table (redundant)

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '3451509c9ce5'
down_revision: Union[str, None] = 'add_payment_tracking'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Step 1: Rename event_activities → user_activity_logs
    op.rename_table('event_activities', 'user_activity_logs')

    # Step 2: Rename event_categories → event_activities
    op.rename_table('event_categories', 'event_activities')

    # Step 3: Add activity_type column to event_activities (formerly event_categories)
    op.add_column('event_activities', sa.Column('activity_type', sa.String(length=50), nullable=True))

    # Step 4: Add event_activity_id to registrations table
    op.add_column('registrations', sa.Column('event_activity_id', sa.Integer(), nullable=True))
    op.create_index(op.f('ix_registrations_event_activity_id'), 'registrations', ['event_activity_id'], unique=False)
    op.create_foreign_key('fk_registrations_event_activity_id', 'registrations', 'event_activities', ['event_activity_id'], ['id'])

    # Step 5: Migrate data - copy event_category_id to event_activity_id
    op.execute("UPDATE registrations SET event_activity_id = event_category_id WHERE event_category_id IS NOT NULL")

    # Step 6: Drop old event_category_id column from registrations
    op.drop_constraint('registrations_event_category_id_fkey', 'registrations', type_='foreignkey')
    op.drop_index('ix_registrations_event_category_id', table_name='registrations')
    op.drop_column('registrations', 'event_category_id')

    # Step 7: Remove event_type from events table
    op.drop_index('ix_events_event_type', table_name='events')
    op.drop_column('events', 'event_type')

    # Step 8: Drop event_activity_types table (no longer needed)
    op.drop_table('event_activity_types')


def downgrade() -> None:
    # Reverse Step 8: Recreate event_activity_types table
    op.create_table('event_activity_types',
        sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
        sa.Column('event_id', sa.INTEGER(), autoincrement=False, nullable=False),
        sa.Column('activity_type', sa.VARCHAR(length=50), autoincrement=False, nullable=False),
        sa.Column('is_primary', sa.BOOLEAN(), autoincrement=False, nullable=False),
        sa.Column('created_at', postgresql.TIMESTAMP(), server_default=sa.text('now()'), autoincrement=False, nullable=False),
        sa.ForeignKeyConstraint(['event_id'], ['events.id'], name='event_activity_types_event_id_fkey', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name='event_activity_types_pkey')
    )
    op.create_index('ix_event_activity_types_event_id', 'event_activity_types', ['event_id'], unique=False)
    op.create_index('ix_event_activity_types_activity_type', 'event_activity_types', ['activity_type'], unique=False)

    # Reverse Step 7: Add back event_type to events table
    op.add_column('events', sa.Column('event_type', sa.VARCHAR(length=50), autoincrement=False, nullable=True))
    op.create_index('ix_events_event_type', 'events', ['event_type'], unique=False)

    # Reverse Step 6: Re-add event_category_id column to registrations
    op.add_column('registrations', sa.Column('event_category_id', sa.INTEGER(), autoincrement=False, nullable=True))
    op.create_index('ix_registrations_event_category_id', 'registrations', ['event_category_id'], unique=False)
    op.create_foreign_key('registrations_event_category_id_fkey', 'registrations', 'event_categories', ['event_category_id'], ['id'])

    # Reverse Step 5: Migrate data back - copy event_activity_id to event_category_id
    op.execute("UPDATE registrations SET event_category_id = event_activity_id WHERE event_activity_id IS NOT NULL")

    # Reverse Step 4: Drop event_activity_id from registrations
    op.drop_constraint('fk_registrations_event_activity_id', 'registrations', type_='foreignkey')
    op.drop_index(op.f('ix_registrations_event_activity_id'), table_name='registrations')
    op.drop_column('registrations', 'event_activity_id')

    # Reverse Step 3: Remove activity_type column from event_activities
    op.drop_column('event_activities', 'activity_type')

    # Reverse Step 2: Rename event_activities → event_categories
    op.rename_table('event_activities', 'event_categories')

    # Reverse Step 1: Rename user_activity_logs → event_activities
    op.rename_table('user_activity_logs', 'event_activities')
