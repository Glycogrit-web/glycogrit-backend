"""Merge migration heads

Revision ID: 64cec31dd3a1
Revises: 20260517_remove_fields, add_audit_logging
Create Date: 2026-05-26 03:50:20.294759

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '64cec31dd3a1'
down_revision: Union[str, None] = ('20260517_remove_fields', 'add_audit_logging')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
