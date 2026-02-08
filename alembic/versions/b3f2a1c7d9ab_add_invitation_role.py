"""add_invitation_role

Revision ID: b3f2a1c7d9ab
Revises: 81eacdf3340b
Create Date: 2026-02-08 12:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b3f2a1c7d9ab'
down_revision: Union[str, None] = '81eacdf3340b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('invitations', sa.Column('role', sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column('invitations', 'role')
