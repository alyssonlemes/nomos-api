"""mensalidade por escritório

Revision ID: t5u6v7w8x9y0
Revises: s4t5u6v7w8x9
Create Date: 2026-11-24 00:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect


revision: str = "t5u6v7w8x9y0"
down_revision: Union[str, None] = "s4t5u6v7w8x9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    colunas = {coluna["name"] for coluna in inspector.get_columns("organizations")}
    if "mensalidade_centavos" not in colunas:
        op.add_column("organizations", sa.Column("mensalidade_centavos", sa.Integer(), nullable=True))
    if "mensalidade_dia" not in colunas:
        op.add_column("organizations", sa.Column("mensalidade_dia", sa.SmallInteger(), nullable=True))

    if "mensalidades" not in inspector.get_table_names():
        op.create_table(
            "mensalidades",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
            sa.Column("competencia", sa.Date(), nullable=False),
            sa.Column("valor_centavos", sa.Integer(), nullable=False),
            sa.Column("pago_em", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.UniqueConstraint("organization_id", "competencia", name="uq_mensalidade_competencia"),
        )
        op.create_index("ix_mensalidades_organization_id", "mensalidades", ["organization_id"])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if "mensalidades" in inspector.get_table_names():
        op.drop_index("ix_mensalidades_organization_id", table_name="mensalidades")
        op.drop_table("mensalidades")
    colunas = {coluna["name"] for coluna in inspector.get_columns("organizations")}
    if "mensalidade_dia" in colunas:
        op.drop_column("organizations", "mensalidade_dia")
    if "mensalidade_centavos" in colunas:
        op.drop_column("organizations", "mensalidade_centavos")
