"""add legal representative fields to organizations

Revision ID: m1n2o3p4q5r6
Revises: k7l8m9n0o1p2
Create Date: 2026-05-17 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "m1n2o3p4q5r6"
down_revision = "k7l8m9n0o1p2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "organizations",
        sa.Column("legal_representative_name", sa.String(length=200), nullable=True),
    )
    op.add_column(
        "organizations",
        sa.Column("legal_representative_document", sa.String(length=20), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("organizations", "legal_representative_document")
    op.drop_column("organizations", "legal_representative_name")
