from typing import Optional, List, Dict
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.organization import Organization
from app.models.user import User
from app.models.client import Client
from app.models.legal_action import LegalAction
from app.schemas.organization import OrganizationCreate, OrganizationUpdate


class OrganizationService:
    """
    Serviço para operações de organização (Business Logic Layer)
    """
    
    @staticmethod
    def get_by_id(db: Session, organization_id: int) -> Optional[Organization]:
        """Busca organização por ID"""
        return db.query(Organization).filter(Organization.id == organization_id).first()
    
    @staticmethod
    def get_by_document(db: Session, document: str) -> Optional[Organization]:
        """Busca organização por documento (CNPJ)"""
        return db.query(Organization).filter(Organization.document == document).first()
    
    @staticmethod
    def get_all(db: Session, skip: int = 0, limit: int = 100, is_active: bool = None) -> List[Organization]:
        """Lista todas as organizações com paginação"""
        query = db.query(Organization)
        
        if is_active is not None:
            query = query.filter(Organization.is_active == is_active)
        
        return query.offset(skip).limit(limit).all()
    
    @staticmethod
    def create(db: Session, org_in: OrganizationCreate) -> Organization:
        """
        Cria uma nova organização
        
        Args:
            db: Sessão do banco de dados
            org_in: Dados da organização a ser criada
        
        Returns:
            Organização criada
        """
        db_org = Organization(
            name=org_in.name,
            document=org_in.document,
            is_active=True
        )
        
        db.add(db_org)
        db.commit()
        db.refresh(db_org)
        return db_org
    
    @staticmethod
    def update(db: Session, organization_id: int, org_in: OrganizationUpdate) -> Optional[Organization]:
        """
        Atualiza uma organização existente
        
        Args:
            db: Sessão do banco de dados
            organization_id: ID da organização
            org_in: Dados para atualização
        
        Returns:
            Organização atualizada ou None se não encontrada
        """
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
    
    @staticmethod
    def delete(db: Session, organization_id: int) -> Optional[Organization]:
        """
        Deleta (desativa) uma organização
        
        Args:
            db: Sessão do banco de dados
            organization_id: ID da organização
        
        Returns:
            Organização deletada ou None se não encontrada
        """
        db_org = OrganizationService.get_by_id(db, organization_id)
        if not db_org:
            return None
        
        # Soft delete - apenas desativa
        db_org.is_active = False
        db.add(db_org)
        db.commit()
        db.refresh(db_org)
        return db_org
    
    @staticmethod
    def get_statistics(db: Session, organization_id: int) -> Dict:
        """
        Retorna estatísticas de uma organização
        
        Args:
            db: Sessão do banco de dados
            organization_id: ID da organização
        
        Returns:
            Dicionário com estatísticas
        """
        total_users = db.query(func.count(User.id)).filter(
            User.organization_id == organization_id
        ).scalar()
        
        total_clients = db.query(func.count(Client.id)).filter(
            Client.organization_id == organization_id
        ).scalar()
        
        total_legal_actions = db.query(func.count(LegalAction.id)).filter(
            LegalAction.organization_id == organization_id
        ).scalar()
        
        return {
            "total_users": total_users,
            "total_clients": total_clients,
            "total_legal_actions": total_legal_actions
        }
    
    @staticmethod
    def add_user_to_organization(db: Session, user_id: int, organization_id: int) -> Optional[User]:
        """
        Vincula um usuário a uma organização
        
        Args:
            db: Sessão do banco de dados
            user_id: ID do usuário
            organization_id: ID da organização
        
        Returns:
            Usuário atualizado ou None se não encontrado
        """
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return None
        
        organization = OrganizationService.get_by_id(db, organization_id)
        if not organization:
            return None
        
        user.organization_id = organization_id
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
