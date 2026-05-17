from typing import Optional, List, Tuple
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_

from app.models.legal_action import LegalAction
from app.models.legal_action_type import LegalActionType
from app.models.legal_action_status import LegalActionStatus
from app.schemas.legal_action import LegalActionCreate, LegalActionUpdate


class LegalActionService:
    """
    Serviço para operações de ações jurídicas
    """
    
    @staticmethod
    def get_by_id(db: Session, action_id: int, organization_id: int, user_id: Optional[int] = None) -> Optional[LegalAction]:
        """Busca ação jurídica por ID (apenas da organização)
        
        Args:
            db: Sessão do banco
            action_id: ID da ação
            organization_id: ID da organização
            user_id: Se fornecido, filtra apenas ações criadas por este usuário
        """
        query = db.query(LegalAction).options(joinedload(LegalAction.action_type), joinedload(LegalAction.legal_status)).filter(
            LegalAction.id == action_id,
            LegalAction.organization_id == organization_id,
        )
        
        if user_id is not None:
            query = query.filter(LegalAction.user_id == user_id)
        
        return query.first()
    
    @staticmethod
    def get_by_number(db: Session, number: str, organization_id: int) -> Optional[LegalAction]:
        """Busca ação jurídica por número do processo"""
        return db.query(LegalAction).filter(
            LegalAction.number == number,
            LegalAction.organization_id == organization_id
        ).first()
    
    @staticmethod
    def get_all(
        db: Session,
        organization_id: int,
        skip: int = 0,
        limit: int = 100,
        legal_status_id: Optional[int] = None,
        client_id: Optional[int] = None,
        search: Optional[str] = None,
        user_id: Optional[int] = None
    ) -> Tuple[List[LegalAction], int]:
        """Lista todas as ações jurídicas da organização com filtros
        
        Args:
            db: Sessão do banco
            organization_id: ID da organização
            skip: Número de registros a pular
            limit: Limite de registros
            legal_status_id: Filtrar por status jurídico
            client_id: Filtrar por cliente
            search: Termo de busca
            user_id: Se fornecido, filtra apenas ações criadas por este usuário
        """
        query = db.query(LegalAction).filter(LegalAction.organization_id == organization_id)
        
        if user_id is not None:
            query = query.filter(LegalAction.user_id == user_id)
        
        if legal_status_id:
            query = query.filter(LegalAction.legal_status_id == legal_status_id)
        
        if client_id:
            query = query.filter(LegalAction.client_id == client_id)
        
        if search:
            search_term = f"%{search}%"
            query = query.filter(
                or_(
                    LegalAction.number.ilike(search_term),
                    LegalAction.title.ilike(search_term)
                )
            )
        
        total = query.count()
        actions = (
            query.options(joinedload(LegalAction.action_type), joinedload(LegalAction.legal_status))
            .offset(skip)
            .limit(limit)
            .all()
        )
        return actions, total
    
    @staticmethod
    def create(db: Session, action_in: LegalActionCreate, organization_id: int, user_id: Optional[int] = None) -> LegalAction:
        """Cria uma nova ação jurídica vinculada à organização."""
        # Garantir que o tipo existe
        action_type = db.query(LegalActionType).filter(LegalActionType.id == action_in.action_type_id).first()
        if not action_type:
            return None  # caller should raise 400

        # Status: se não vier, usar pre_trial por padrão
        status_id = action_in.legal_status_id
        if status_id is None:
            default_status = db.query(LegalActionStatus).filter(LegalActionStatus.code == "pre_trial").first()
            if not default_status:
                raise ValueError("Status jurídico padrão 'pre_trial' não encontrado")
            status_id = default_status.id
        else:
            if not db.query(LegalActionStatus).filter(LegalActionStatus.id == status_id).first():
                raise ValueError("Status jurídico não encontrado")

        db_action = LegalAction(
            number=action_in.number,
            title=action_in.title,
            description=action_in.description,
            client_id=action_in.client_id,
            organization_id=organization_id,
            user_id=user_id,
            action_type_id=action_in.action_type_id,
            legal_status_id=status_id,
            court_name=action_in.court_name,
            filing_date=action_in.filing_date,
            is_active=True,
        )
        
        db.add(db_action)
        db.commit()
        db.refresh(db_action)
        return LegalActionService.get_by_id(db, db_action.id, organization_id)
    
    @staticmethod
    def update(
        db: Session,
        action_id: int,
        action_in: LegalActionUpdate,
        organization_id: int,
        user_id: Optional[int] = None
    ) -> Optional[LegalAction]:
        """Atualiza uma ação jurídica
        
        Args:
            db: Sessão do banco
            action_id: ID da ação
            action_in: Dados de atualização
            organization_id: ID da organização
            user_id: Se fornecido, valida se a ação pertence a este usuário
        """
        db_action = LegalActionService.get_by_id(db, action_id, organization_id, user_id)
        if not db_action:
            return None
        
        update_data = action_in.model_dump(exclude_unset=True)

        # If frontend provided a status code (e.g. {"legal_status": "litigation"}),
        # resolve it to an id and set `legal_status_id` for the update.
        if "legal_status" in update_data:
            code = update_data.get("legal_status")
            status = db.query(LegalActionStatus).filter(LegalActionStatus.code == code).first()
            if not status:
                raise ValueError("Status jurídico não encontrado (código inválido)")
            update_data["legal_status_id"] = status.id
            # remove the string key so we only set the id on the model
            update_data.pop("legal_status", None)

        if "action_type_id" in update_data:
            if not db.query(LegalActionType).filter(
                LegalActionType.id == update_data["action_type_id"]
            ).first():
                raise ValueError("Tipo de ação jurídica não encontrado")

        if "legal_status_id" in update_data:
            if not db.query(LegalActionStatus).filter(
                LegalActionStatus.id == update_data["legal_status_id"]
            ).first():
                raise ValueError("Status jurídico não encontrado")

        for field, value in update_data.items():
            setattr(db_action, field, value)
        
        db.add(db_action)
        db.commit()
        db.refresh(db_action)
        return LegalActionService.get_by_id(db, action_id, organization_id, user_id)
    
    @staticmethod
    def delete(db: Session, action_id: int, organization_id: int, user_id: Optional[int] = None) -> Optional[LegalAction]:
        """Deleta uma ação jurídica
        
        Args:
            db: Sessão do banco
            action_id: ID da ação
            organization_id: ID da organização
            user_id: Se fornecido, valida se a ação pertence a este usuário
        """
        db_action = LegalActionService.get_by_id(db, action_id, organization_id, user_id)
        if not db_action:
            return None
        
        db.delete(db_action)
        db.commit()
        return db_action
