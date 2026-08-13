"""add status column to activity_columns

Revision ID: k7l8m9n0o1p2
Revises: h2i3j4k5l6m7
Create Date: 2026-05-07 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "k7l8m9n0o1p2"
down_revision = "h2i3j4k5l6m7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Adicionar coluna 'status' à tabela 'activity_columns'
    op.add_column(
        "activity_columns",
        sa.Column("status", sa.String(50), nullable=True),
    )

    # Adicionar constraint de uniqueness para organization_id + status (quando status não é null)
    op.create_unique_constraint(
        "uq_activity_columns_org_status",
        "activity_columns",
        ["organization_id", "status"],
    )


def downgrade() -> None:
    # Remover constraint
    op.drop_constraint(
        "uq_activity_columns_org_status",
        "activity_columns",
    )
    
    # Remover coluna 'status'
    op.drop_column("activity_columns", "status")
