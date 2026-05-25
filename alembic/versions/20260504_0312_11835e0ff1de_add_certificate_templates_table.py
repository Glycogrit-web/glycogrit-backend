"""add_certificate_templates_table

Revision ID: 11835e0ff1de
Revises: 20260503_razorpay
Create Date: 2026-05-04 03:12:05.096509

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '11835e0ff1de'
down_revision: str | None = '20260503_razorpay'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Create certificate_templates table
    op.create_table(
        'certificate_templates',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('template_html', sa.Text(), nullable=False),
        sa.Column('template_css', sa.Text(), nullable=True),
        sa.Column('background_image_url', sa.String(length=500), nullable=True),
        sa.Column('logo_url', sa.String(length=500), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_default', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('created_by_user_id', sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['created_by_user_id'], ['users.id'], ondelete='SET NULL')
    )

    # Create indexes for certificate_templates
    op.create_index('idx_certificate_templates_active', 'certificate_templates', ['is_active'])
    op.create_index('idx_certificate_templates_default', 'certificate_templates', ['is_default'])

    # Add certificate_template_id to events table
    op.add_column('events', sa.Column('certificate_template_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk_events_certificate_template',
        'events', 'certificate_templates',
        ['certificate_template_id'], ['id'],
        ondelete='SET NULL'
    )

    # Add certificate fields to user_rewards table
    op.add_column('user_rewards', sa.Column('certificate_url', sa.String(length=500), nullable=True))
    op.add_column('user_rewards', sa.Column('certificate_number', sa.String(length=100), nullable=True))

    # Add download tracking fields
    op.add_column('user_rewards', sa.Column('download_count', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('user_rewards', sa.Column('download_limit', sa.Integer(), nullable=False, server_default='10'))
    op.add_column('user_rewards', sa.Column('last_downloaded_at', sa.DateTime(), nullable=True))

    # Create index and unique constraint for certificate_number
    op.create_index('idx_user_rewards_certificate', 'user_rewards', ['reward_type', 'certificate_url'])
    op.create_unique_constraint('uq_user_rewards_certificate_number', 'user_rewards', ['certificate_number'])
    op.create_index('idx_user_rewards_downloads', 'user_rewards', ['download_count', 'download_limit'])


def downgrade() -> None:
    # Drop constraints and indexes from user_rewards
    op.drop_index('idx_user_rewards_downloads', 'user_rewards')
    op.drop_constraint('uq_user_rewards_certificate_number', 'user_rewards', type_='unique')
    op.drop_index('idx_user_rewards_certificate', 'user_rewards')

    # Drop columns from user_rewards
    op.drop_column('user_rewards', 'last_downloaded_at')
    op.drop_column('user_rewards', 'download_limit')
    op.drop_column('user_rewards', 'download_count')
    op.drop_column('user_rewards', 'certificate_number')
    op.drop_column('user_rewards', 'certificate_url')

    # Drop foreign key and column from events
    op.drop_constraint('fk_events_certificate_template', 'events', type_='foreignkey')
    op.drop_column('events', 'certificate_template_id')

    # Drop indexes from certificate_templates
    op.drop_index('idx_certificate_templates_default', 'certificate_templates')
    op.drop_index('idx_certificate_templates_active', 'certificate_templates')

    # Drop certificate_templates table
    op.drop_table('certificate_templates')
