"""add unique constraint to email

Revision ID: 004
Revises: 003
Create Date: 2026-04-18

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = '004'
down_revision = '003'
branch_labels = None
depends_on = None


def upgrade():
    """Add unique constraint to email column"""
    # Create unique constraint on email
    op.create_unique_constraint('uq_users_email', 'users', ['email'])


def downgrade():
    """Remove unique constraint from email column"""
    # Drop unique constraint
    op.drop_constraint('uq_users_email', 'users', type_='unique')
