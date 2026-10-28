from typing import Optional, List
from sqlalchemy.orm import Session

from app.models.organization import Organization
from app.models.user import User
from app.models.access_profile import AccessProfile
from app.schemas.organization import OrganizationCreate, OrganizationUpdate
from app.core.perfis import NOME_ADMINISTRADOR, PERFIS_PADRAO, papel_legado


class OrganizationService:
    """Serviço para operações de organização"""
    
    @staticmethod
    def get_by_id(db: Session, organization_id: int) -> Optional[Organization]:
        """Busca organização por ID"""
        return db.query(Organization).filter(Organization.id == organization_id).first()
    
    @staticmethod
    def get_by_document(db: Session, document: str) -> Optional[Organization]:
        """Busca organização por documento (CNPJ)"""
        return db.query(Organization).filter(Organization.document == document).first()
    
    @staticmethod
    def get_by_owner(db: Session, owner_id: int) -> Optional[Organization]:
        """Busca organização por proprietário"""
        return db.query(Organization).filter(Organization.owner_id == owner_id).first()
    
    @staticmethod
    def create(db: Session, org_in: OrganizationCreate, owner_id: int) -> Organization:
        """
        Cria uma nova organização e vincula o usuário como proprietário
        
        Args:
            db: Sessão do banco de dados
            org_in: Dados da organização
            owner_id: ID do usuário que está criando a organização
        
        Returns:
            Organização criada
        """
        # Criar organização
        db_org = Organization(
            name=org_in.name,
            document=org_in.document,
            legal_representative_name=org_in.legal_representative_name,
            legal_representative_document=org_in.legal_representative_document,
            owner_id=owner_id,
            is_active=True
        )
        db.add(db_org)
        db.flush()

        for item in PERFIS_PADRAO:
            db.add(
                AccessProfile(
                    organization_id=db_org.id,
                    name=item["nome"],
                    description=item["descricao"],
                    is_system=True,
                    isolate_data=item["isolate_data"],
                    permissions=item["permissoes"],
                )
            )
        db.flush()

        admin = (
            db.query(AccessProfile)
            .filter(AccessProfile.organization_id == db_org.id, AccessProfile.name == NOME_ADMINISTRADOR)
            .first()
        )
        user = db.query(User).filter(User.id == owner_id).first()
        if user:
            user.organization_id = db_org.id
            user.profile_id = admin.id if admin else None
            user.role = papel_legado(NOME_ADMINISTRADOR, eh_dono=True)
            db.add(user)

        db.commit()
        db.refresh(db_org)
        return db_org
    
    @staticmethod
    def update(db: Session, organization_id: int, org_in: OrganizationUpdate) -> Optional[Organization]:
        """Atualiza uma organização"""
        db_org = OrganizationService.get_by_id(db, organization_id)
        if not db_org:
            return None
        
        update_data = org_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_org, field, value)
        
        db.add(db_org)
        db.commit()
        db.refresh(db_org)
        return db_org
