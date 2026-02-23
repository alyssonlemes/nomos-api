"""legal_action_types_catalog

Revision ID: a1b2c3d4e5f6
Revises: 81eacdf3340b
Create Date: 2026-02-20

Cria tabela legal_action_types (catálogo), migra dados de legal_actions.action_type
(enum) para action_type_id (FK) e remove o enum.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "b3f2a1c7d9ab"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Tipos padrão (antigo enum LegalActionType)
DEFAULT_TYPES = [
    ("labor", "Trabalhista"),
    ("civil", "Cível"),
    ("criminal", "Criminal"),
    ("admin", "Administrativa"),
    ("tax", "Tributária"),
    ("commercial", "Comercial"),
    ("family", "Família"),
    ("real_estate", "Imóvel"),
    ("other", "Outra"),
]


def upgrade() -> None:
    # 1. Criar tabela legal_action_types
    op.create_table(
        "legal_action_types",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_legal_action_types_id"), "legal_action_types", ["id"], unique=False)
    op.create_index(op.f("ix_legal_action_types_name"), "legal_action_types", ["name"], unique=False)
    op.create_index(op.f("ix_legal_action_types_code"), "legal_action_types", ["code"], unique=True)

    # 2. Inserir tipos padrão (IDs fixos para o UPDATE abaixo)
    conn = op.get_bind()
    for idx, (code, name) in enumerate(DEFAULT_TYPES, start=1):
        conn.execute(
            sa.text(
                "INSERT INTO legal_action_types (id, name, code) VALUES (:id, :name, :code)"
            ),
            {"id": idx, "name": name, "code": code},
        )
    # Ajustar sequence para o próximo id
    conn.execute(sa.text("SELECT setval(pg_get_serial_sequence('legal_action_types', 'id'), 9)"))

    # 3. Adicionar coluna action_type_id (nullable primeiro)
    op.add_column(
        "legal_actions",
        sa.Column("action_type_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_legal_actions_action_type_id",
        "legal_actions",
        "legal_action_types",
        ["action_type_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    # 4. Migrar dados: preencher action_type_id a partir do enum action_type
    op.execute("""
        UPDATE legal_actions la
        SET action_type_id = lat.id
        FROM legal_action_types lat
        WHERE lat.code = CAST(la.action_type AS VARCHAR)
    """)
    # Preencher linhas que não deram match com tipo "other"
    op.execute("""
        UPDATE legal_actions
        SET action_type_id = (SELECT id FROM legal_action_types WHERE code = 'other' LIMIT 1)
        WHERE action_type_id IS NULL
    """)

    # 5. Tornar action_type_id NOT NULL (após preencher)
    op.alter_column(
        "legal_actions",
        "action_type_id",
        existing_type=sa.Integer(),
        nullable=False,
    )

    # 6. Remover coluna antiga action_type (enum)
    op.drop_column("legal_actions", "action_type")


def downgrade() -> None:
    # Recriar coluna action_type como enum
    action_type_enum = sa.Enum(
        "labor", "civil", "criminal", "admin", "tax",
        "commercial", "family", "real_estate", "other",
        name="legalactiontype",
    )
    action_type_enum.create(op.get_bind(), checkfirst=True)
    op.add_column(
        "legal_actions",
        sa.Column("action_type", action_type_enum, nullable=True),
    )

    # Preencher action_type a partir de legal_action_types
    op.execute("""
        UPDATE legal_actions la
        SET action_type = lat.code::legalactiontype
        FROM legal_action_types lat
        WHERE lat.id = la.action_type_id
    """)
    op.alter_column(
        "legal_actions",
        "action_type",
        nullable=False,
    )

    # Remover FK e coluna action_type_id
    op.drop_constraint("fk_legal_actions_action_type_id", "legal_actions", type_="foreignkey")
    op.drop_column("legal_actions", "action_type_id")

    # Remover tabela legal_action_types
    op.drop_index(op.f("ix_legal_action_types_code"), table_name="legal_action_types")
    op.drop_index(op.f("ix_legal_action_types_name"), table_name="legal_action_types")
    op.drop_index(op.f("ix_legal_action_types_id"), table_name="legal_action_types")
    op.drop_table("legal_action_types")
    action_type_enum.drop(op.get_bind(), checkfirst=True)
