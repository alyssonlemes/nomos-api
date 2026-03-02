from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.models.client import Client
from app.schemas.client import ClientCreate, ClientUpdate


class ClientService:
    """Serviço para operações de cliente vinculados à organização"""
    
    @staticmethod
    def get_by_id(db: Session, client_id: int, organization_id: int, user_id: Optional[int] = None) -> Optional[Client]:
        """Busca cliente por ID da organização
        
        Args:
            db: Sessão do banco
            client_id: ID do cliente
            organization_id: ID da organização
            user_id: Se fornecido, filtra apenas clientes criados por este usuário
        """
        query = db.query(Client).filter(
            Client.id == client_id,
            Client.organization_id == organization_id
        )
        
        if user_id is not None:
            query = query.filter(Client.user_id == user_id)
        
        return query.first()
    
    @staticmethod
    def get_by_document(db: Session, document: str, organization_id: int) -> Optional[Client]:
        """Busca cliente por documento (CPF/CNPJ) da organização"""
        return db.query(Client).filter(
            Client.document == document,
            Client.organization_id == organization_id
        ).first()
    
    @staticmethod
    def get_all(
        db: Session,
        organization_id: int,
        skip: int = 0,
        limit: int = 100,
        search: Optional[str] = None,
        user_id: Optional[int] = None
    ) -> tuple[List[Client], int]:
        """Lista clientes da organização com paginação e busca
        
        Args:
            db: Sessão do banco
            organization_id: ID da organização
            skip: Número de registros a pular
            limit: Limite de registros
            search: Termo de busca
            user_id: Se fornecido, filtra apenas clientes criados por este usuário
        """
        query = db.query(Client).filter(Client.organization_id == organization_id)
        
        if user_id is not None:
            query = query.filter(Client.user_id == user_id)
        
        if search:
            search_term = f"%{search}%"
            query = query.filter(
                or_(
                    Client.name.ilike(search_term),
                    Client.email.ilike(search_term),
                    Client.document.ilike(search_term)
                )
            )
        
        total = query.count()
        clients = query.offset(skip).limit(limit).all()
        return clients, total
    
    @staticmethod
    def create(db: Session, client_in: ClientCreate, organization_id: int, user_id: int = None) -> Client:
        """Cria um novo cliente vinculado à organização"""
        db_client = Client(
            name=client_in.name,
            email=client_in.email,
            phone=client_in.phone,
            document=client_in.document,
            client_type=client_in.client_type,
            status=client_in.status,
            address=client_in.address,
            city=client_in.city,
            state=client_in.state,
            zip_code=client_in.zip_code,
            company_name=client_in.company_name,
            organization_id=organization_id,
            user_id=user_id
        )
        db.add(db_client)
        db.commit()
        db.refresh(db_client)
        return db_client
    
    @staticmethod
    def update(
        db: Session,
        client_id: int,
        client_in: ClientUpdate,
        organization_id: int,
        user_id: Optional[int] = None
    ) -> Optional[Client]:
        """Atualiza um cliente da organização
        
        Args:
            db: Sessão do banco
            client_id: ID do cliente
            client_in: Dados de atualização
            organization_id: ID da organização
            user_id: Se fornecido, valida se o cliente pertence a este usuário
        """
        db_client = ClientService.get_by_id(db, client_id, organization_id, user_id)
        if not db_client:
            return None
        
        update_data = client_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_client, field, value)
        
        db.add(db_client)
        db.commit()
        db.refresh(db_client)
        return db_client
    
    @staticmethod
    def delete(db: Session, client_id: int, organization_id: int, user_id: Optional[int] = None) -> Optional[Client]:
        """Deleta um cliente da organização
        
        Args:
            db: Sessão do banco
            client_id: ID do cliente
            organization_id: ID da organização
            user_id: Se fornecido, valida se o cliente pertence a este usuário
        """
        db_client = ClientService.get_by_id(db, client_id, organization_id, user_id)
        if not db_client:
            return None
        
        db.delete(db_client)
        db.commit()
        return db_client
