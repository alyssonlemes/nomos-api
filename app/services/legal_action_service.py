from typing import Optional, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import or_
from datetime import date

from app.models.legal_action import LegalAction, Party, CaseMovement, Deadline, LegalStatus, DeadlineStatus
from app.schemas.legal_action import (
    LegalActionCreate, LegalActionUpdate, PartyCreate, PartyUpdate,
    CaseMovementCreate, CaseMovementUpdate, DeadlineCreate, DeadlineUpdate
)


class LegalActionService:
    """
    Serviço para operações de ações jurídicas
    """
    
    @staticmethod
    def get_by_id(db: Session, action_id: int, organization_id: int) -> Optional[LegalAction]:
        """Busca ação jurídica por ID (apenas da organização)"""
        return db.query(LegalAction).filter(
            LegalAction.id == action_id,
            LegalAction.organization_id == organization_id
        ).first()
    
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
        legal_status: Optional[LegalStatus] = None,
        action_type: Optional[str] = None,
        client_id: Optional[int] = None,
        search: Optional[str] = None
    ) -> Tuple[List[LegalAction], int]:
        """Lista todas as ações jurídicas da organização com filtros"""
        query = db.query(LegalAction).filter(LegalAction.organization_id == organization_id)
        
        if legal_status:
            query = query.filter(LegalAction.legal_status == legal_status)
        
        if action_type:
            query = query.filter(LegalAction.action_type == action_type)
        
        if client_id:
            query = query.filter(LegalAction.client_id == client_id)
        
        if search:
            search_term = f"%{search}%"
            query = query.filter(
                or_(
                    LegalAction.number.ilike(search_term),
                    LegalAction.title.ilike(search_term),
                    LegalAction.court_name.ilike(search_term)
                )
            )
        
        total = query.count()
        actions = query.offset(skip).limit(limit).all()
        return actions, total
    
    @staticmethod
    def create(db: Session, action_in: LegalActionCreate, organization_id: int, user_id: Optional[int] = None) -> LegalAction:
        """Cria uma nova ação jurídica"""
        db_action = LegalAction(
            number=action_in.number,
            title=action_in.title,
            description=action_in.description,
            client_id=action_in.client_id,
            organization_id=organization_id,
            user_id=user_id,
            action_type=action_in.action_type,
            legal_status=action_in.legal_status,
            court_name=action_in.court_name,
            court_segment=action_in.court_segment,
            filing_date=action_in.filing_date,
            is_active=True
        )
        
        db.add(db_action)
        db.commit()
        db.refresh(db_action)
        return db_action
    
    @staticmethod
    def update(
        db: Session,
        action_id: int,
        action_in: LegalActionUpdate,
        organization_id: int
    ) -> Optional[LegalAction]:
        """Atualiza uma ação jurídica"""
        db_action = LegalActionService.get_by_id(db, action_id, organization_id)
        if not db_action:
            return None
        
        update_data = action_in.model_dump(exclude_unset=True)
        
        for field, value in update_data.items():
            setattr(db_action, field, value)
        
        db.add(db_action)
        db.commit()
        db.refresh(db_action)
        return db_action
    
    @staticmethod
    def delete(db: Session, action_id: int, organization_id: int) -> Optional[LegalAction]:
        """Deleta uma ação jurídica"""
        db_action = LegalActionService.get_by_id(db, action_id, organization_id)
        if not db_action:
            return None
        
        db.delete(db_action)
        db.commit()
        return db_action
    
    @staticmethod
    def get_statistics(db: Session, organization_id: int) -> dict:
        """Retorna estatísticas das ações jurídicas da organização"""
        total = db.query(LegalAction).filter(LegalAction.organization_id == organization_id).count()
        
        active = db.query(LegalAction).filter(
            LegalAction.organization_id == organization_id,
            LegalAction.legal_status.in_([
                LegalStatus.FILING, LegalStatus.LITIGATION, LegalStatus.EXECUTION, LegalStatus.APPEAL
            ])
        ).count()
        
        finalized = db.query(LegalAction).filter(
            LegalAction.organization_id == organization_id,
            LegalAction.legal_status == LegalStatus.FINALIZED
        ).count()
        
        return {
            "total": total,
            "active": active,
            "finalized": finalized
        }


class PartyService:
    """Serviço para operações com partes do processo"""
    
    @staticmethod
    def create(db: Session, party_in: PartyCreate, action_id: int) -> Party:
        """Cria uma nova parte"""
        db_party = Party(
            legal_action_id=action_id,
            name=party_in.name,
            party_type=party_in.party_type,
            email=party_in.email,
            phone=party_in.phone,
            document=party_in.document,
            legal_representative=party_in.legal_representative
        )
        
        db.add(db_party)
        db.commit()
        db.refresh(db_party)
        return db_party
    
    @staticmethod
    def update(db: Session, party_id: int, party_in: PartyUpdate, action_id: int) -> Optional[Party]:
        """Atualiza uma parte"""
        db_party = db.query(Party).filter(
            Party.id == party_id,
            Party.legal_action_id == action_id
        ).first()
        
        if not db_party:
            return None
        
        update_data = party_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_party, field, value)
        
        db.add(db_party)
        db.commit()
        db.refresh(db_party)
        return db_party
    
    @staticmethod
    def delete(db: Session, party_id: int, action_id: int) -> Optional[Party]:
        """Deleta uma parte"""
        db_party = db.query(Party).filter(
            Party.id == party_id,
            Party.legal_action_id == action_id
        ).first()
        
        if not db_party:
            return None
        
        db.delete(db_party)
        db.commit()
        return db_party


class CaseMovementService:
    """Serviço para operações com movimentações"""
    
    @staticmethod
    def create(db: Session, movement_in: CaseMovementCreate, action_id: int) -> CaseMovement:
        """Cria uma nova movimentação"""
        db_movement = CaseMovement(
            legal_action_id=action_id,
            title=movement_in.title,
            description=movement_in.description,
            movement_type=movement_in.movement_type,
            movement_date=movement_in.movement_date,
            notification_date=movement_in.notification_date,
            source=movement_in.source
        )
        
        db.add(db_movement)
        db.commit()
        db.refresh(db_movement)
        return db_movement
    
    @staticmethod
    def update(
        db: Session,
        movement_id: int,
        movement_in: CaseMovementUpdate,
        action_id: int
    ) -> Optional[CaseMovement]:
        """Atualiza uma movimentação"""
        db_movement = db.query(CaseMovement).filter(
            CaseMovement.id == movement_id,
            CaseMovement.legal_action_id == action_id
        ).first()
        
        if not db_movement:
            return None
        
        update_data = movement_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_movement, field, value)
        
        db.add(db_movement)
        db.commit()
        db.refresh(db_movement)
        return db_movement
    
    @staticmethod
    def delete(db: Session, movement_id: int, action_id: int) -> Optional[CaseMovement]:
        """Deleta uma movimentação"""
        db_movement = db.query(CaseMovement).filter(
            CaseMovement.id == movement_id,
            CaseMovement.legal_action_id == action_id
        ).first()
        
        if not db_movement:
            return None
        
        db.delete(db_movement)
        db.commit()
        return db_movement


class DeadlineService:
    """Serviço para operações com prazos"""
    
    @staticmethod
    def create(db: Session, deadline_in: DeadlineCreate, action_id: int) -> Deadline:
        """Cria um novo prazo"""
        db_deadline = Deadline(
            legal_action_id=action_id,
            title=deadline_in.title,
            description=deadline_in.description,
            deadline_type=deadline_in.deadline_type,
            due_date=deadline_in.due_date,
            status=deadline_in.status
        )
        
        db.add(db_deadline)
        db.commit()
        db.refresh(db_deadline)
        return db_deadline
    
    @staticmethod
    def update(
        db: Session,
        deadline_id: int,
        deadline_in: DeadlineUpdate,
        action_id: int
    ) -> Optional[Deadline]:
        """Atualiza um prazo"""
        db_deadline = db.query(Deadline).filter(
            Deadline.id == deadline_id,
            Deadline.legal_action_id == action_id
        ).first()
        
        if not db_deadline:
            return None
        
        update_data = deadline_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_deadline, field, value)
        
        db.add(db_deadline)
        db.commit()
        db.refresh(db_deadline)
        return db_deadline
    
    @staticmethod
    def delete(db: Session, deadline_id: int, action_id: int) -> Optional[Deadline]:
        """Deleta um prazo"""
        db_deadline = db.query(Deadline).filter(
            Deadline.id == deadline_id,
            Deadline.legal_action_id == action_id
        ).first()
        
        if not db_deadline:
            return None
        
        db.delete(db_deadline)
        db.commit()
        return db_deadline
    
    @staticmethod
    def get_pending_deadlines(db: Session, organization_id: int) -> List[Deadline]:
        """Retorna prazos pendentes da organização"""
        return db.query(Deadline).join(LegalAction).filter(
            LegalAction.organization_id == organization_id,
            Deadline.status == DeadlineStatus.PENDING,
            Deadline.due_date >= date.today()
        ).order_by(Deadline.due_date).all()
    
    @staticmethod
    def get_overdue_deadlines(db: Session, organization_id: int) -> List[Deadline]:
        """Retorna prazos vencidos da organização"""
        return db.query(Deadline).join(LegalAction).filter(
            LegalAction.organization_id == organization_id,
            Deadline.status == DeadlineStatus.PENDING,
            Deadline.due_date < date.today()
        ).order_by(Deadline.due_date).all()
