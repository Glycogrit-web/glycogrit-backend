"""merge_courier_cert_heads

Revision ID: b2b3683ed41c
Revises: 20260602_cert_template, 20260607_cert_distance_sport, 20260609_001_courier_selection
Create Date: 2026-06-09 14:30:54.037449

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b2b3683ed41c'
down_revision: Union[str, None] = ('20260602_cert_template', '20260607_cert_distance_sport', '20260609_001_courier_selection')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
