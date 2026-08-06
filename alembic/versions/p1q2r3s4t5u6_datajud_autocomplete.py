"""datajud autocomplete: extend legal_actions + create processo_partes/movimentos

Revision ID: p1q2r3s4t5u6
Revises: n2o3p4q5r6s7
Create Date: 2026-08-03 00:00:00.000000

Mudanças:
    1. Adiciona 16 novas colunas DataJud à tabela legal_actions
    2. Cria tabela processo_partes (1:N com legal_actions)
    3. Cria tabela processo_movimentos (1:N com legal_actions)
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = "p1q2r3s4t5u6"
down_revision: Union[str, None] = "n2o3p4q5r6s7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_exists(inspector, table: str, column: str) -> bool:
    """Verifica se uma coluna já existe na tabela (idempotência)."""
    return any(c["name"] == column for c in inspector.get_columns(table))


def _table_exists(inspector, table: str) -> bool:
    """Verifica se a tabela já existe (idempotência)."""
    return table in inspector.get_table_names()


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    # ─────────────────────────────────────────────────────────────────────────
    # 1. Evoluir tabela legal_actions (+16 colunas DataJud)
    # ─────────────────────────────────────────────────────────────────────────
    new_columns = [
        ("tribunal",                    sa.String(),        True),
        ("comarca",                     sa.String(),        True),
        ("vara",                        sa.String(),        True),
        ("orgao_julgador",              sa.String(),        True),
        ("competencia",                 sa.String(),        True),
        ("magistrado",                  sa.String(),        True),
        ("classe_processual_codigo",    sa.String(),        True),
        ("classe_processual_nome",      sa.String(),        True),
        ("assuntos_json",               sa.Text(),          True),
        ("data_distribuicao",           sa.Date(),          True),
        ("valor_causa",                 sa.Numeric(15, 2),  True),
        ("segredo_justica",             sa.Boolean(),       True),
        ("datajud_synced_at",           sa.DateTime(timezone=True), True),
        ("datajud_last_update",         sa.String(),        True),
        ("datajud_preserve_manual",     sa.Boolean(),       True),
    ]

    for col_name, col_type, nullable in new_columns:
        if not _column_exists(inspector, "legal_actions", col_name):
            server_default = None
            if col_name == "segredo_justica":
                server_default = sa.text("false")
            elif col_name == "datajud_preserve_manual":
                server_default = sa.text("false")
            op.add_column(
                "legal_actions",
                sa.Column(col_name, col_type, nullable=nullable, server_default=server_default),
            )

    # Índices adicionais em legal_actions
    existing_indexes = {idx["name"] for idx in inspector.get_indexes("legal_actions")}
    if "idx_legal_action_tribunal" not in existing_indexes:
        op.create_index("idx_legal_action_tribunal", "legal_actions", ["tribunal"])
    if "idx_legal_action_classe" not in existing_indexes:
        op.create_index("idx_legal_action_classe", "legal_actions", ["classe_processual_codigo"])

    # ─────────────────────────────────────────────────────────────────────────
    # 2. Criar tabela processo_partes
    # ─────────────────────────────────────────────────────────────────────────
    if not _table_exists(inspector, "processo_partes"):
        op.create_table(
            "processo_partes",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("legal_action_id", sa.Integer(), nullable=False),
            sa.Column("polo", sa.String(20), nullable=True),
            sa.Column("tipo_participacao", sa.String(30), nullable=True),
            sa.Column("nome", sa.String(), nullable=False),
            sa.Column("documento", sa.String(), nullable=True),
            sa.Column("oab", sa.String(), nullable=True),
            sa.Column("client_id", sa.Integer(), nullable=True),
            sa.ForeignKeyConstraint(
                ["legal_action_id"], ["legal_actions.id"], ondelete="CASCADE"
            ),
            sa.ForeignKeyConstraint(
                ["client_id"], ["clients.id"], ondelete="SET NULL"
            ),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("idx_processo_partes_legal_action", "processo_partes", ["legal_action_id"])
        op.create_index("idx_processo_partes_documento", "processo_partes", ["documento"])
        op.create_index("idx_processo_partes_client", "processo_partes", ["client_id"])

    # ─────────────────────────────────────────────────────────────────────────
    # 3. Criar tabela processo_movimentos
    # ─────────────────────────────────────────────────────────────────────────
    if not _table_exists(inspector, "processo_movimentos"):
        op.create_table(
            "processo_movimentos",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("legal_action_id", sa.Integer(), nullable=False),
            sa.Column("codigo", sa.String(), nullable=True),
            sa.Column("nome", sa.String(), nullable=False),
            sa.Column("data_hora", sa.DateTime(timezone=True), nullable=True),
            sa.Column("complemento_json", sa.Text(), nullable=True),
            sa.ForeignKeyConstraint(
                ["legal_action_id"], ["legal_actions.id"], ondelete="CASCADE"
            ),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            "idx_processo_movimentos_legal_action", "processo_movimentos", ["legal_action_id"]
        )
        op.create_index(
            "idx_processo_movimentos_data", "processo_movimentos", ["legal_action_id", "data_hora"]
        )
        op.create_index(
            "idx_processo_movimentos_codigo", "processo_movimentos", ["codigo"]
        )


def downgrade() -> None:
    # Remover índices e tabelas novas
    op.drop_index("idx_processo_movimentos_codigo", table_name="processo_movimentos")
    op.drop_index("idx_processo_movimentos_data", table_name="processo_movimentos")
    op.drop_index("idx_processo_movimentos_legal_action", table_name="processo_movimentos")
    op.drop_table("processo_movimentos")

    op.drop_index("idx_processo_partes_client", table_name="processo_partes")
    op.drop_index("idx_processo_partes_documento", table_name="processo_partes")
    op.drop_index("idx_processo_partes_legal_action", table_name="processo_partes")
    op.drop_table("processo_partes")

    # Remover colunas de legal_actions (em ordem reversa)
    for col_name in [
        "datajud_preserve_manual", "datajud_last_update", "datajud_synced_at",
        "segredo_justica", "valor_causa", "data_distribuicao", "assuntos_json",
        "classe_processual_nome", "classe_processual_codigo", "magistrado",
        "competencia", "orgao_julgador", "vara", "comarca", "tribunal",
    ]:
        op.drop_column("legal_actions", col_name)
