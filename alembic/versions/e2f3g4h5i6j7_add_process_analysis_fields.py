"""add_process_analysis_fields_to_jurimetria_dataset

Revision ID: e2f3g4h5i6j7
Revises: d1e2f3g4h5i6
Create Date: 2026-03-02

Adiciona campos necessários para análise de processos judiciais:
- area_juridica_principal: classificação por área (Criminal, Família, etc.)
- classe_principal_nome: nome legível da classe processual
- assuntos_json: JSON com assuntos relacionados
- data_fim: data de encerramento inferida dos movimentos
- status_processo: 'finalizado' ou 'em_andamento'
- movimento_encerramento: nome do movimento que determinou o encerramento
- duracao_dias: dias entre ajuizamento e encerramento
- updated_at: timestamp de atualização

Referência: Master Prompt Seções 2, 3 e 4.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = "e2f3g4h5i6j7"
down_revision: Union[str, None] = "d1e2f3g4h5i6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)

    existing_columns = [col["name"] for col in inspector.get_columns("jurimetria_dataset")]

    # Adicionar novas colunas (apenas se não existirem)
    new_columns = {
        "area_juridica_principal": sa.Column("area_juridica_principal", sa.String(), nullable=True),
        "classe_principal_nome": sa.Column("classe_principal_nome", sa.String(), nullable=True),
        "assuntos_json": sa.Column("assuntos_json", sa.Text(), nullable=True),
        "data_fim": sa.Column("data_fim", sa.Date(), nullable=True),
        "status_processo": sa.Column("status_processo", sa.String(), nullable=True, server_default="em_andamento"),
        "movimento_encerramento": sa.Column("movimento_encerramento", sa.String(), nullable=True),
        "duracao_dias": sa.Column("duracao_dias", sa.Integer(), nullable=True),
        "updated_at": sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    }

    for col_name, col_def in new_columns.items():
        if col_name not in existing_columns:
            op.add_column("jurimetria_dataset", col_def)

    # Criar índices para as novas colunas
    existing_indexes = [idx["name"] for idx in inspector.get_indexes("jurimetria_dataset")]

    indexes_to_create = [
        ("idx_jurimetria_area_juridica", ["area_juridica_principal"]),
        ("idx_jurimetria_status", ["status_processo"]),
        ("idx_jurimetria_area_status", ["area_juridica_principal", "status_processo"]),
    ]

    for idx_name, idx_columns in indexes_to_create:
        if idx_name not in existing_indexes:
            op.create_index(idx_name, "jurimetria_dataset", idx_columns, unique=False)


def downgrade() -> None:
    # Remover índices
    op.drop_index("idx_jurimetria_area_status", table_name="jurimetria_dataset")
    op.drop_index("idx_jurimetria_status", table_name="jurimetria_dataset")
    op.drop_index("idx_jurimetria_area_juridica", table_name="jurimetria_dataset")

    # Remover colunas
    op.drop_column("jurimetria_dataset", "updated_at")
    op.drop_column("jurimetria_dataset", "duracao_dias")
    op.drop_column("jurimetria_dataset", "movimento_encerramento")
    op.drop_column("jurimetria_dataset", "status_processo")
    op.drop_column("jurimetria_dataset", "data_fim")
    op.drop_column("jurimetria_dataset", "assuntos_json")
    op.drop_column("jurimetria_dataset", "classe_principal_nome")
    op.drop_column("jurimetria_dataset", "area_juridica_principal")
