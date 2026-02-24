"""legal_action_statuses_catalog

Revision ID: b7c8d9e0f1a2
Revises: a1b2c3d4e5f6
Create Date: 2026-02-20

Cria tabela legal_action_statuses (catálogo), migra dados de legal_actions.legal_status
(enum) para legal_status_id (FK) e remove o enum.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision: str = "b7c8d9e0f1a2"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Status padrão (antigo enum LegalStatus)
DEFAULT_STATUSES = [
    ("pre_trial", "Pré-processual"),
    ("filing", "Ajuizamento"),
    ("litigation", "Contencioso"),
    ("execution", "Execução"),
    ("appeal", "Recurso"),
    ("finalized", "Finalizado"),
    ("archived", "Arquivado"),
]


def _table_exists(conn, name: str) -> bool:
    return inspect(conn).has_table(name)


def _column_exists(conn, table: str, column: str) -> bool:
    return column in [c["name"] for c in inspect(conn).get_columns(table)]


def upgrade() -> None:
    conn = op.get_bind()

    # 1. Criar tabela legal_action_statuses (se não existir)
    if not _table_exists(conn, "legal_action_statuses"):
        op.create_table(
            "legal_action_statuses",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("name", sa.String(length=100), nullable=False),
            sa.Column("code", sa.String(length=50), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            op.f("ix_legal_action_statuses_id"),
            "legal_action_statuses",
            ["id"],
            unique=False,
        )
        op.create_index(
            op.f("ix_legal_action_statuses_name"),
            "legal_action_statuses",
            ["name"],
            unique=False,
        )
        op.create_index(
            op.f("ix_legal_action_statuses_code"),
            "legal_action_statuses",
            ["code"],
            unique=True,
        )

        # 2. Inserir status padrão (IDs fixos)
        for idx, (code, name) in enumerate(DEFAULT_STATUSES, start=1):
            conn.execute(
                sa.text(
                    "INSERT INTO legal_action_statuses (id, name, code) "
                    "VALUES (:id, :name, :code)"
                ),
                {"id": idx, "name": name, "code": code},
            )
        conn.execute(
            sa.text(
                "SELECT setval(pg_get_serial_sequence('legal_action_statuses', 'id'), 7)"
            )
        )
    else:
        # Tabela já existe: garantir que tem os 7 status (ex.: run anterior criou tabela vazia)
        for idx, (code, name) in enumerate(DEFAULT_STATUSES, start=1):
            conn.execute(
                sa.text(
                    "INSERT INTO legal_action_statuses (id, name, code) "
                    "VALUES (:id, :name, :code) ON CONFLICT (id) DO NOTHING"
                ),
                {"id": idx, "name": name, "code": code},
            )

    # 3. Adicionar coluna legal_status_id em legal_actions (se não existir)
    if not _column_exists(conn, "legal_actions", "legal_status_id"):
        op.add_column(
            "legal_actions",
            sa.Column("legal_status_id", sa.Integer(), nullable=True),
        )
        op.create_foreign_key(
            "fk_legal_actions_legal_status_id",
            "legal_actions",
            "legal_action_statuses",
            ["legal_status_id"],
            ["id"],
            ondelete="RESTRICT",
        )

    # 4. Migrar dados do enum legal_status para legal_status_id (se coluna antiga existir)
    if _column_exists(conn, "legal_actions", "legal_status"):
        op.execute(
            """
            UPDATE legal_actions la
            SET legal_status_id = las.id
            FROM legal_action_statuses las
            WHERE las.code = CAST(la.legal_status AS VARCHAR)
            """
        )
    # Sempre preencher NULLs com pre_trial (caso coluna já exista de run anterior)
    op.execute(
        """
        UPDATE legal_actions
        SET legal_status_id = (SELECT id FROM legal_action_statuses WHERE code = 'pre_trial' LIMIT 1)
        WHERE legal_status_id IS NULL
        """
    )

    # 5. Tornar legal_status_id NOT NULL (se ainda for nullable)
    if _column_exists(conn, "legal_actions", "legal_status_id"):
        op.alter_column(
            "legal_actions",
            "legal_status_id",
            existing_type=sa.Integer(),
            nullable=False,
        )

    # 6. Remover coluna antiga legal_status (enum) se existir
    if _column_exists(conn, "legal_actions", "legal_status"):
        op.drop_column("legal_actions", "legal_status")


def downgrade() -> None:
    # Recriar enum legalstatus para a coluna antiga
    legal_status_enum = sa.Enum(
        "pre_trial",
        "filing",
        "litigation",
        "execution",
        "appeal",
        "finalized",
        "archived",
        name="legalstatus",
    )
    legal_status_enum.create(op.get_bind(), checkfirst=True)

    op.add_column(
        "legal_actions",
        sa.Column("legal_status", legal_status_enum, nullable=True),
    )

    # Preencher legal_status a partir de legal_action_statuses
    op.execute(
        """
        UPDATE legal_actions la
        SET legal_status = las.code::legalstatus
        FROM legal_action_statuses las
        WHERE las.id = la.legal_status_id
        """
    )
    op.alter_column(
        "legal_actions",
        "legal_status",
        nullable=False,
    )

    # Remover FK e coluna legal_status_id
    op.drop_constraint(
        "fk_legal_actions_legal_status_id",
        "legal_actions",
        type_="foreignkey",
    )
    op.drop_column("legal_actions", "legal_status_id")

    # Remover tabela legal_action_statuses
    op.drop_index(
        op.f("ix_legal_action_statuses_code"), table_name="legal_action_statuses"
    )
    op.drop_index(
        op.f("ix_legal_action_statuses_name"), table_name="legal_action_statuses"
    )
    op.drop_index(
        op.f("ix_legal_action_statuses_id"), table_name="legal_action_statuses"
    )
    op.drop_table("legal_action_statuses")
    legal_status_enum.drop(op.get_bind(), checkfirst=True)

