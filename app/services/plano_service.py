"""Conta vagas do plano do escritório e recusa o que passar do teto."""

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.domain.planos import Plano, cabe, obter_plano
from app.models.invitation import Invitation, InvitationStatus
from app.models.legal_action import LegalAction
from app.models.organization import Organization
from app.models.user import User
from app.schemas.organization import OrganizationResponse
from app.services.organization_service import OrganizationService

class LimiteDoPlano(Exception):
    pass

class PlanoService:
    @staticmethod
    def atual(db: Session, organization_id: int) -> Plano:
        organizacao = OrganizationService.get_by_id(db, organization_id)
        codigo = organizacao.plano if organizacao else None
        return obter_plano(codigo)

    @staticmethod
    def usuarios(db: Session, organization_id: int) -> int:
        total = (
            db.query(func.count(User.id))
            .filter(User.organization_id == organization_id)
            .scalar()
        )
        return int(total or 0)

    @staticmethod
    def convites_pendentes(db: Session, organization_id: int) -> int:
        total = (
            db.query(func.count(Invitation.id))
            .filter(
                Invitation.organization_id == organization_id,
                Invitation.status == InvitationStatus.PENDING,
            )
            .scalar()
        )
        return int(total or 0)

    @staticmethod
    def processos(db: Session, organization_id: int) -> int:
        total = (
            db.query(func.count(LegalAction.id))
            .filter(LegalAction.organization_id == organization_id)
            .scalar()
        )
        return int(total or 0)

    @staticmethod
    def montar_resposta(db: Session, organizacao: Organization) -> OrganizationResponse:
        plano = obter_plano(organizacao.plano)
        return OrganizationResponse(
            id=organizacao.id,
            name=organizacao.name,
            document=organizacao.document,
            legal_representative_name=organizacao.legal_representative_name,
            legal_representative_document=organizacao.legal_representative_document,
            owner_id=organizacao.owner_id,
            is_active=bool(organizacao.is_active),
            plano=plano.codigo,
            plano_nome=plano.nome,
            limite_usuarios=plano.usuarios,
            limite_processos=plano.processos,
            usuarios_em_uso=PlanoService.usuarios(db, organizacao.id),
            processos_em_uso=PlanoService.processos(db, organizacao.id),
            created_at=organizacao.created_at,
            updated_at=organizacao.updated_at,
        )

    @staticmethod
    def garantir_novo_usuario(db: Session, organization_id: int) -> None:
        plano = PlanoService.atual(db, organization_id)
        em_uso = PlanoService.usuarios(db, organization_id) + PlanoService.convites_pendentes(db, organization_id)
        if not cabe(em_uso, plano.usuarios):
            raise LimiteDoPlano(
                f"O plano {plano.nome} permite até {plano.usuarios} usuários neste escritório."
            )

    @staticmethod
    def garantir_aceite(db: Session, organization_id: int) -> None:
        plano = PlanoService.atual(db, organization_id)
        if not cabe(PlanoService.usuarios(db, organization_id), plano.usuarios):
            raise LimiteDoPlano(
                f"O plano {plano.nome} permite até {plano.usuarios} usuários neste escritório."
            )

    @staticmethod
    def garantir_novo_processo(db: Session, organization_id: int) -> None:
        plano = PlanoService.atual(db, organization_id)
        if not cabe(PlanoService.processos(db, organization_id), plano.processos):
            raise LimiteDoPlano(
                f"O plano {plano.nome} permite até {plano.processos} processos neste escritório."
            )
