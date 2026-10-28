"""perfis de acesso com crud por modulo

Revision ID: q2r3s4t5u6v7
Revises: p1q2r3s4t5u6
Create Date: 2026-10-28 00:00:00.000000

Cria access_profiles, vincula usuários e convites e copia os papéis
legados para os perfis padrão de cada organização.
"""
from typing import Sequence, Union

import json

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect, text

from app.core.perfis import NOME_ADMINISTRADOR, PERFIS_PADRAO, nome_do_papel, papel_legado


revision: str = "q2r3s4t5u6v7"
down_revision: Union[str, None] = "p1q2r3s4t5u6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_exists(inspector, table: str, column: str) -> bool:
    if table not in inspector.get_table_names():
        return False
    return any(c["name"] == column for c in inspector.get_columns(table))


def _table_exists(inspector, table: str) -> bool:
    return table in inspector.get_table_names()


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    if not _table_exists(inspector, "access_profiles"):
        op.create_table(
            "access_profiles",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
            sa.Column("name", sa.String(), nullable=False),
            sa.Column("description", sa.String(), nullable=True),
            sa.Column("is_system", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("isolate_data", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("permissions", sa.JSON(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.UniqueConstraint("organization_id", "name", name="uq_access_profile_org_name"),
        )
        op.create_index("ix_access_profiles_organization_id", "access_profiles", ["organization_id"])

    inspector = inspect(bind)
    if not _column_exists(inspector, "users", "profile_id"):
        op.add_column("users", sa.Column("profile_id", sa.Integer(), nullable=True))
        op.create_foreign_key("fk_users_profile_id", "users", "access_profiles", ["profile_id"], ["id"], ondelete="SET NULL")
        op.create_index("ix_users_profile_id", "users", ["profile_id"])

    inspector = inspect(bind)
    if not _column_exists(inspector, "invitations", "profile_id"):
        op.add_column("invitations", sa.Column("profile_id", sa.Integer(), nullable=True))
        op.create_foreign_key(
            "fk_invitations_profile_id",
            "invitations",
            "access_profiles",
            ["profile_id"],
            ["id"],
            ondelete="SET NULL",
        )
        op.create_index("ix_invitations_profile_id", "invitations", ["profile_id"])

    orgs = bind.execute(text("SELECT id, owner_id FROM organizations")).fetchall()
    for org_id, owner_id in orgs:
        for item in PERFIS_PADRAO:
            exists = bind.execute(
                text("SELECT id FROM access_profiles WHERE organization_id = :org AND name = :name"),
                {"org": org_id, "name": item["nome"]},
            ).first()
            if exists:
                continue
            bind.execute(
                text(
                    """
                    INSERT INTO access_profiles
                        (organization_id, name, description, is_system, isolate_data, permissions, created_at)
                    VALUES
                        (:org, :name, :description, true, :isolate, CAST(:permissions AS json), CURRENT_TIMESTAMP)
                    """
                ),
                {
                    "org": org_id,
                    "name": item["nome"],
                    "description": item["descricao"],
                    "isolate": item["isolate_data"],
                    "permissions": json.dumps(item["permissoes"]),
                },
            )

        users = bind.execute(
            text("SELECT id, role FROM users WHERE organization_id = :org AND profile_id IS NULL"),
            {"org": org_id},
        ).fetchall()
        for user_id, role in users:
            eh_dono = user_id == owner_id
            nome = nome_do_papel(role, eh_dono=eh_dono)
            perfil = bind.execute(
                text("SELECT id FROM access_profiles WHERE organization_id = :org AND name = :name"),
                {"org": org_id, "name": nome},
            ).first()
            if not perfil:
                continue
            bind.execute(
                text(
                    """
                    UPDATE users
                    SET profile_id = :pid,
                        role = COALESCE(role, :legacy)
                    WHERE id = :id AND profile_id IS NULL
                    """
                ),
                {"pid": perfil[0], "legacy": papel_legado(nome, eh_dono=eh_dono), "id": user_id},
            )

    invites = bind.execute(
        text("SELECT id, organization_id, role FROM invitations WHERE profile_id IS NULL")
    ).fetchall()
    for invite_id, org_id, role in invites:
        nome = nome_do_papel(role or "member", eh_dono=False)
        if (role or "").lower() in {"admin", "owner"}:
            nome = NOME_ADMINISTRADOR
        perfil = bind.execute(
            text("SELECT id FROM access_profiles WHERE organization_id = :org AND name = :name"),
            {"org": org_id, "name": nome},
        ).first()
        if not perfil:
            continue
        bind.execute(
            text("UPDATE invitations SET profile_id = :pid WHERE id = :id AND profile_id IS NULL"),
            {"pid": perfil[0], "id": invite_id},
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if _column_exists(inspector, "invitations", "profile_id"):
        op.drop_index("ix_invitations_profile_id", table_name="invitations")
        op.drop_constraint("fk_invitations_profile_id", "invitations", type_="foreignkey")
        op.drop_column("invitations", "profile_id")
    if _column_exists(inspector, "users", "profile_id"):
        op.drop_index("ix_users_profile_id", table_name="users")
        op.drop_constraint("fk_users_profile_id", "users", type_="foreignkey")
        op.drop_column("users", "profile_id")
    if _table_exists(inspector, "access_profiles"):
        op.drop_index("ix_access_profiles_organization_id", table_name="access_profiles")
        op.drop_table("access_profiles")
