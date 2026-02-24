"""legal_action_statuses_id_sequence

Revision ID: c8d9e0f1a2b3
Revises: b7c8d9e0f1a2
Create Date: 2026-02-24

Garante que a coluna id de legal_action_statuses use uma sequência (SERIAL),
para permitir INSERT de novos status sem informar id (evita erro de restrição).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "c8d9e0f1a2b3"
down_revision: Union[str, None] = "b7c8d9e0f1a2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    # Só aplica em PostgreSQL
    if conn.dialect.name != "postgresql":
        return

    # 1. Criar sequência se não existir (nome que o PostgreSQL usa para SERIAL)
    seq_name = "legal_action_statuses_id_seq"
    conn.execute(
        sa.text(
            f"""
            CREATE SEQUENCE IF NOT EXISTS {seq_name}
            OWNED BY legal_action_statuses.id;
            """
        )
    )

    # 2. Ajustar o valor da sequência para o próximo id após o maior existente
    conn.execute(
        sa.text(
            f"""
            SELECT setval(
                '{seq_name}'::regclass,
                COALESCE((SELECT MAX(id) FROM legal_action_statuses), 1)
            );
            """
        )
    )

    # 3. Definir default da coluna id para nextval da sequência
    op.alter_column(
        "legal_action_statuses",
        "id",
        existing_type=sa.Integer(),
        server_default=sa.text(f"nextval('{seq_name}'::regclass)"),
        existing_nullable=False,
    )


def downgrade() -> None:
    conn = op.get_bind()
    if conn.dialect.name != "postgresql":
        return

    # Remover default da coluna id (não removemos a sequência para evitar quebrar dados)
    op.alter_column(
        "legal_action_statuses",
        "id",
        existing_type=sa.Integer(),
        server_default=None,
        existing_nullable=False,
    )
