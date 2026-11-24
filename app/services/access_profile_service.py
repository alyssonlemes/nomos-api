from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from app.core.perfis import (
    NOME_ADMINISTRADOR,
    NOME_POR_PAPEL,
    PERFIS_PADRAO,
    eh_administrador,
    nome_do_papel,
    papel_legado,
    permissoes_como_mapa,
)
from app.models.access_profile import AccessProfile
from app.models.organization import Organization
from app.models.user import User

class AcessoNegado(Exception):
    pass

class PerfilInvalido(Exception):
    pass

class AccessProfileService:
    @staticmethod
    def listar(db: Session, organization_id: int) -> list[AccessProfile]:
        AccessProfileService.garantir_padrao(db, organization_id)
        return (
            db.query(AccessProfile)
            .filter(AccessProfile.organization_id == organization_id)
            .order_by(AccessProfile.name.asc())
            .all()
        )

    @staticmethod
    def buscar(db: Session, profile_id: int, organization_id: int) -> Optional[AccessProfile]:
        return (
            db.query(AccessProfile)
            .filter(AccessProfile.id == profile_id, AccessProfile.organization_id == organization_id)
            .first()
        )

    @staticmethod
    def buscar_por_nome(db: Session, organization_id: int, nome: str) -> Optional[AccessProfile]:
        return (
            db.query(AccessProfile)
            .filter(AccessProfile.organization_id == organization_id, AccessProfile.name == nome)
            .first()
        )

    @staticmethod
    def garantir_padrao(db: Session, organization_id: int) -> list[AccessProfile]:
        existentes = {
            perfil.name: perfil
            for perfil in db.query(AccessProfile).filter(AccessProfile.organization_id == organization_id).all()
        }
        criou = False
        for item in PERFIS_PADRAO:
            if item["nome"] in existentes:
                continue
            db.add(
                AccessProfile(
                    organization_id=organization_id,
                    name=item["nome"],
                    description=item["descricao"],
                    is_system=True,
                    isolate_data=item["isolate_data"],
                    permissions=item["permissoes"],
                )
            )
            criou = True
        if criou:
            db.commit()
        return (
            db.query(AccessProfile)
            .filter(AccessProfile.organization_id == organization_id)
            .order_by(AccessProfile.name.asc())
            .all()
        )

    @staticmethod
    def vincular_usuario(db: Session, user: User, organization_id: int, nome: str, eh_dono: bool = False) -> User:
        perfis = AccessProfileService.garantir_padrao(db, organization_id)
        perfil = next((item for item in perfis if item.name == nome), None)
        if perfil is None:
            perfil = next(item for item in perfis if item.name == nome_do_papel(None))
        user.organization_id = organization_id
        user.profile_id = perfil.id
        user.role = papel_legado(perfil.name, eh_dono)
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def garantir_vinculo(db: Session, user: User) -> User:
        if not user.organization_id or user.profile_id:
            return user
        org = db.query(Organization).filter(Organization.id == user.organization_id).first()
        eh_dono = bool(org and org.owner_id == user.id)
        nome = nome_do_papel(user.role, eh_dono=eh_dono)
        return AccessProfileService.vincular_usuario(db, user, user.organization_id, nome, eh_dono=eh_dono)

    @staticmethod
    def atualizar(
        db: Session,
        profile_id: int,
        organization_id: int,
        permissions: list | dict,
        isolate_data: bool,
    ) -> Optional[AccessProfile]:
        perfil = AccessProfileService.buscar(db, profile_id, organization_id)
        if perfil is None:
            return None
        perfil.isolate_data = isolate_data
        if perfil.name != NOME_ADMINISTRADOR:
            perfil.permissions = permissoes_como_mapa(permissions, aplicar_limites=True)
            flag_modified(perfil, "permissions")
        db.add(perfil)
        db.commit()
        db.refresh(perfil)
        return perfil

    @staticmethod
    def contar_administradores(db: Session, organization_id: int, excluir_id: int | None = None) -> int:
        admin_ids = db.query(AccessProfile.id).filter(
            AccessProfile.organization_id == organization_id,
            AccessProfile.name == NOME_ADMINISTRADOR,
        )
        query = db.query(User).filter(
            User.organization_id == organization_id,
            User.is_active.is_(True),
            User.profile_id.in_(admin_ids),
        )
        if excluir_id is not None:
            query = query.filter(User.id != excluir_id)
        return query.count()

    @staticmethod
    def resolver_por_papel(db: Session, organization_id: int, role: str | None) -> Optional[AccessProfile]:
        AccessProfileService.garantir_padrao(db, organization_id)
        nome = NOME_POR_PAPEL.get((role or "").strip().lower())
        if not nome:
            return None
        return AccessProfileService.buscar_por_nome(db, organization_id, nome)

    @staticmethod
    def atribuir(db: Session, ator: User, alvo: User, profile_id: int) -> User:
        if ator.id == alvo.id:
            raise AcessoNegado("Você não pode alterar o próprio perfil.")
        if not ator.organization_id or alvo.organization_id != ator.organization_id:
            raise PerfilInvalido("Usuário não encontrado na sua organização.")

        perfil = AccessProfileService.buscar(db, profile_id, ator.organization_id)
        if perfil is None:
            raise PerfilInvalido("Perfil inválido para esta organização.")

        ator_admin = eh_administrador(ator)
        if not ator_admin:
            from app.core.perfis import tem_permissao_usuario

            if not tem_permissao_usuario(ator, "usuarios", "editar"):
                raise AcessoNegado("Você não tem permissão para alterar o perfil de usuários.")
            if eh_administrador(alvo) or perfil.name == NOME_ADMINISTRADOR:
                raise AcessoNegado("Apenas o administrador pode alterar ou atribuir o perfil Administrador.")

        if eh_administrador(alvo) and perfil.name != NOME_ADMINISTRADOR:
            if AccessProfileService.contar_administradores(db, ator.organization_id, excluir_id=alvo.id) == 0:
                raise PerfilInvalido("Não é possível remover o último administrador da organização.")

        org = db.query(Organization).filter(Organization.id == ator.organization_id).first()
        alvo.profile_id = perfil.id
        alvo.role = papel_legado(perfil.name, bool(org and org.owner_id == alvo.id))
        db.add(alvo)
        db.commit()
        db.refresh(alvo)
        return alvo
