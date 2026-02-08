"""make_legal_action_number_unique_per_organization

Revision ID: 81eacdf3340b
Revises: 65acd36c44e4
Create Date: 2026-02-08 11:47:43.078695

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '81eacdf3340b'
down_revision: Union[str, None] = '65acd36c44e4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint("legal_actions_number_key", "legal_actions", type_="unique")
    op.create_unique_constraint(
        "uq_legal_actions_org_number",
        "legal_actions",
        ["organization_id", "number"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_legal_actions_org_number", "legal_actions", type_="unique")
    op.create_unique_constraint(
        "legal_actions_number_key",
        "legal_actions",
        ["number"],
    )
