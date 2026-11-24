"""plano da organização

Revision ID: s4t5u6v7w8x9
Revises: r3s4t5u6v7w8
Create Date: 2026-11-24 00:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect


revision: str = "s4t5u6v7w8x9"
down_revision: Union[str, None] = "r3s4t5u6v7w8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    colunas = {coluna["name"] for coluna in inspector.get_columns("organizations")}
    if "plano" not in colunas:
        op.add_column(
            "organizations",
            sa.Column("plano", sa.String(length=32), nullable=False, server_default="essencial"),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    colunas = {coluna["name"] for coluna in inspector.get_columns("organizations")}
    if "plano" in colunas:
        op.drop_column("organizations", "plano")
