"""Add goodie unlock and verification fields

Revision ID: 20260425_goodie_unlock
Revises: 20260424_0413_b096bd29fb22
Create Date: 2026-04-25

"""
import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = '20260425_goodie_unlock'
down_revision = 'b096bd29fb22'
branch_labels = None
depends_on = None


def upgrade():
    # Add unlock and verification fields to user_goodies table
    op.add_column('user_goodies', sa.Column('is_unlocked', sa.Enum('true', 'false', name='boolean_enum_unlocked'), nullable=False, server_default='false'))
    op.add_column('user_goodies', sa.Column('is_verified', sa.Enum('true', 'false', name='boolean_enum_verified'), nullable=False, server_default='false'))
    op.add_column('user_goodies', sa.Column('unlocked_by_admin_id', sa.Integer(), nullable=True))
    op.add_column('user_goodies', sa.Column('verified_by_admin_id', sa.Integer(), nullable=True))
    op.add_column('user_goodies', sa.Column('unlocked_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('user_goodies', sa.Column('verified_at', sa.DateTime(timezone=True), nullable=True))

    # Create indexes for new fields
    op.create_index(op.f('ix_user_goodies_is_unlocked'), 'user_goodies', ['is_unlocked'], unique=False)

    # Create foreign key constraints
    op.create_foreign_key('fk_user_goodies_unlocked_by_admin', 'user_goodies', 'users', ['unlocked_by_admin_id'], ['id'])
    op.create_foreign_key('fk_user_goodies_verified_by_admin', 'user_goodies', 'users', ['verified_by_admin_id'], ['id'])


def downgrade():
    # Drop foreign key constraints
    op.drop_constraint('fk_user_goodies_verified_by_admin', 'user_goodies', type_='foreignkey')
    op.drop_constraint('fk_user_goodies_unlocked_by_admin', 'user_goodies', type_='foreignkey')

    # Drop index
    op.drop_index(op.f('ix_user_goodies_is_unlocked'), table_name='user_goodies')

    # Drop columns
    op.drop_column('user_goodies', 'verified_at')
    op.drop_column('user_goodies', 'unlocked_at')
    op.drop_column('user_goodies', 'verified_by_admin_id')
    op.drop_column('user_goodies', 'unlocked_by_admin_id')
    op.drop_column('user_goodies', 'is_verified')
    op.drop_column('user_goodies', 'is_unlocked')

    # Drop enum types
    op.execute('DROP TYPE IF EXISTS boolean_enum_verified')
    op.execute('DROP TYPE IF EXISTS boolean_enum_unlocked')
