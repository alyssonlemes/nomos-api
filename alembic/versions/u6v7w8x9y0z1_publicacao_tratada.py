"""marca de publicação tratada

Revision ID: u6v7w8x9y0z1
Revises: t5u6v7w8x9y0
Create Date: 2026-11-26 00:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect


revision: str = "u6v7w8x9y0z1"
down_revision: Union[str, None] = "t5u6v7w8x9y0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    colunas = {coluna["name"] for coluna in inspector.get_columns("processo_movimentos")}
    if "tratado_em" not in colunas:
        op.add_column("processo_movimentos", sa.Column("tratado_em", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    colunas = {coluna["name"] for coluna in inspector.get_columns("processo_movimentos")}
    if "tratado_em" in colunas:
        op.drop_column("processo_movimentos", "tratado_em")
