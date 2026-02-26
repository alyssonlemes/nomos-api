"""create_jurimetria_dataset

Revision ID: d1e2f3g4h5i6
Revises: c8d9e0f1a2b3
Create Date: 2026-02-26

Cria a tabela jurimetria_dataset para armazenar o dataset de jurimetria
utilizado pelo pipeline de treino de ML.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = "d1e2f3g4h5i6"
down_revision: Union[str, None] = "c8d9e0f1a2b3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)

    # Se a tabela já existir (criada anteriormente via create_all ou manualmente),
    # não tenta recriar para evitar erro de DuplicateTable.
    if inspector.has_table("jurimetria_dataset"):
        return

    op.create_table(
        "jurimetria_dataset",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("tribunal", sa.String(), nullable=False),
        sa.Column("numero_processo", sa.String(), nullable=False),
        sa.Column("data_ajuizamento", sa.Date(), nullable=False),
        sa.Column("data_ultima_movimentacao", sa.Date(), nullable=True),
        sa.Column("tempo_tramitacao_dias", sa.Integer(), nullable=True),
        sa.Column("classe_processual", sa.String(), nullable=True),
        sa.Column("assunto_codigo", sa.String(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "tribunal",
            "numero_processo",
            name="uq_jurimetria_tribunal_numero",
        ),
    )

    op.create_index(
        "idx_jurimetria_tribunal_data",
        "jurimetria_dataset",
        ["tribunal", "data_ajuizamento"],
        unique=False,
    )
    op.create_index(
        "idx_jurimetria_classe_assunto",
        "jurimetria_dataset",
        ["classe_processual", "assunto_codigo"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("idx_jurimetria_classe_assunto", table_name="jurimetria_dataset")
    op.drop_index("idx_jurimetria_tribunal_data", table_name="jurimetria_dataset")
    op.drop_table("jurimetria_dataset")

