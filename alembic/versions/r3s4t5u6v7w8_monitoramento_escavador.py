"""monitoramento escavador e prazos

Revision ID: r3s4t5u6v7w8
Revises: q2r3s4t5u6v7
Create Date: 2026-11-24 00:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect


revision: str = "r3s4t5u6v7w8"
down_revision: Union[str, None] = "q2r3s4t5u6v7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(inspector, table: str) -> bool:
    return table in inspector.get_table_names()


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    if not _table_exists(inspector, "processo_monitoramentos"):
        op.create_table(
            "processo_monitoramentos",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
            sa.Column("legal_action_id", sa.Integer(), sa.ForeignKey("legal_actions.id", ondelete="CASCADE"), nullable=False),
            sa.Column("escavador_id", sa.BigInteger(), nullable=True),
            sa.Column("numero_cnj", sa.String(), nullable=False),
            sa.Column("numero_digitos", sa.String(length=20), nullable=False),
            sa.Column("status", sa.String(length=32), nullable=False, server_default="PENDENTE"),
            sa.Column("frequencia", sa.String(length=16), nullable=False, server_default="DIARIA"),
            sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("data_ultima_verificacao", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.UniqueConstraint("legal_action_id", name="uq_processo_monitoramento_acao"),
        )
        op.create_index("idx_processo_monitoramento_org_ativo", "processo_monitoramentos", ["organization_id", "ativo", "status"])
        op.create_index("idx_processo_monitoramento_escavador", "processo_monitoramentos", ["escavador_id"])
        op.create_index("idx_processo_monitoramento_digitos", "processo_monitoramentos", ["numero_digitos"])

    if not _table_exists(inspector, "processo_prazos"):
        op.create_table(
            "processo_prazos",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
            sa.Column("legal_action_id", sa.Integer(), sa.ForeignKey("legal_actions.id", ondelete="CASCADE"), nullable=False),
            sa.Column("escavador_movimentacao_id", sa.String(), nullable=False),
            sa.Column("origem", sa.String(length=32), nullable=False),
            sa.Column("conteudo", sa.Text(), nullable=False),
            sa.Column("data_movimentacao", sa.Date(), nullable=True),
            sa.Column("dias_prazo", sa.Integer(), nullable=True),
            sa.Column("data_vencimento", sa.Date(), nullable=True),
            sa.Column("status", sa.String(length=16), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.UniqueConstraint("legal_action_id", "escavador_movimentacao_id", name="uq_processo_prazo_movimentacao"),
        )
        op.create_index("idx_processo_prazo_org_status", "processo_prazos", ["organization_id", "status"])
        op.create_index("idx_processo_prazo_acao", "processo_prazos", ["legal_action_id", "status"])

    if not _table_exists(inspector, "escavador_callbacks"):
        op.create_table(
            "escavador_callbacks",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("uuid", sa.String(length=80), nullable=False),
            sa.Column("event", sa.String(length=64), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.UniqueConstraint("uuid", name="uq_escavador_callback_uuid"),
        )
        op.create_index("ix_escavador_callbacks_uuid", "escavador_callbacks", ["uuid"])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if _table_exists(inspector, "escavador_callbacks"):
        op.drop_table("escavador_callbacks")
    if _table_exists(inspector, "processo_prazos"):
        op.drop_table("processo_prazos")
    if _table_exists(inspector, "processo_monitoramentos"):
        op.drop_table("processo_monitoramentos")
