"""add_proof_image_url

Revision ID: add_proof_image_url
Revises: add_activity_source
Create Date: 2026-04-29 04:20:00

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_proof_image_url'
down_revision = 'add_activity_source'
branch_labels = None
depends_on = None


def upgrade():
    # Add proof_image_url field to user_challenge_progress table
    op.add_column('user_challenge_progress',
        sa.Column('proof_image_url', sa.String(length=500), nullable=True,
                 comment='Cloudflare R2 URL for user-uploaded proof image'))


def downgrade():
    # Drop column
    op.drop_column('user_challenge_progress', 'proof_image_url')
