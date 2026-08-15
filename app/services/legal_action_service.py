from typing import Optional, List, Tuple
from sqlalchemy.orm import Session, joinedload, selectinload
from sqlalchemy import or_

from app.models.client import Client
from app.models.legal_action import LegalAction
from app.models.legal_action_type import LegalActionType
from app.models.legal_action_status import LegalActionStatus
from app.models.user import User
from app.schemas.legal_action import LegalActionCreate, LegalActionUpdate
from app.services.notification_service import NotificationService


class LegalActionService:
    """
    Serviço para operações de ações jurídicas
    """

    @staticmethod
    def _resolve_assigned_users(
        db: Session,
        *,
        organization_id: int,
        user_ids: list[int],
    ) -> list[User]:
        if not user_ids:
            return []
        unique_ids = list(dict.fromkeys(user_ids))
        users = (
            db.query(User)
            .filter(User.id.in_(unique_ids), User.organization_id == organization_id)
            .all()
        )
        if len(users) != len(unique_ids):
            raise ValueError("Um ou mais usuarios nao pertencem a organizacao")
        return users
    
    @staticmethod
    def get_by_id(db: Session, action_id: int, organization_id: int, user_id: Optional[int] = None) -> Optional[LegalAction]:
        """Busca ação jurídica por ID (apenas da organização)
        
        Args:
            db: Sessão do banco
            action_id: ID da ação
            organization_id: ID da organização
            user_id: Se fornecido, filtra apenas ações criadas por este usuário
        """
        query = db.query(LegalAction).options(
            joinedload(LegalAction.action_type),
            joinedload(LegalAction.legal_status),
            selectinload(LegalAction.assigned_users),
            selectinload(LegalAction.partes),
            selectinload(LegalAction.movimentos),
        ).filter(
            LegalAction.id == action_id,
            LegalAction.organization_id == organization_id,
        )
        
        if user_id is not None:
            query = query.filter(
                or_(
                    LegalAction.user_id == user_id,
                    LegalAction.assigned_users.any(User.id == user_id),
                )
            )
        
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
            query = query.filter(
                or_(
                    LegalAction.user_id == user_id,
                    LegalAction.assigned_users.any(User.id == user_id),
                )
            )
        
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
            query.options(
                joinedload(LegalAction.action_type),
                joinedload(LegalAction.legal_status),
                selectinload(LegalAction.assigned_users),
            )
            .offset(skip)
            .limit(limit)
            .all()
        )
        return actions, total
    
    @staticmethod
    def create(db: Session, action_in: LegalActionCreate, organization_id: int, user_id: Optional[int] = None) -> LegalAction:
        """Cria uma nova ação jurídica vinculada à organização."""
        # Validar se o cliente pertence à organização
        if action_in.client_id:
            client = db.query(Client).filter(
                Client.id == action_in.client_id,
                Client.organization_id == organization_id
            ).first()
            if not client:
                raise ValueError("Cliente não encontrado ou não pertence a esta organização")

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
            tribunal=action_in.tribunal,
            comarca=action_in.comarca,
            vara=action_in.vara,
            orgao_julgador=action_in.orgao_julgador,
            competencia=action_in.competencia,
            magistrado=action_in.magistrado,
            classe_processual_codigo=action_in.classe_processual_codigo,
            classe_processual_nome=action_in.classe_processual_nome,
            assuntos_json=action_in.assuntos_json,
            data_distribuicao=action_in.data_distribuicao,
            valor_causa=action_in.valor_causa,
            segredo_justica=action_in.segredo_justica,
            is_active=True,
        )

        requested_user_ids = action_in.user_ids or []
        assigned_ids = set(requested_user_ids)
        if user_id is not None:
            assigned_ids.add(user_id)
        assigned_users = LegalActionService._resolve_assigned_users(
            db,
            organization_id=organization_id,
            user_ids=list(assigned_ids),
        )
        db_action.assigned_users = assigned_users
        
        db.add(db_action)
        db.commit()
        db.refresh(db_action)
        
        from app.models.processo_parte import ProcessoParte
        from app.models.processo_movimento import ProcessoMovimento

        if getattr(action_in, "partes", None):
            for p in action_in.partes:
                db_parte = ProcessoParte(**p.model_dump(), legal_action_id=db_action.id)
                db.add(db_parte)
                
        if getattr(action_in, "movimentos", None):
            for m in action_in.movimentos:
                db_mov = ProcessoMovimento(**m.model_dump(), legal_action_id=db_action.id)
                db.add(db_mov)
                
        if getattr(action_in, "partes", None) or getattr(action_in, "movimentos", None):
            db.commit()

        for assigned_user in assigned_users:
            if user_id is not None and assigned_user.id == user_id:
                continue
            NotificationService.create(
                db,
                user_id=assigned_user.id,
                organization_id=organization_id,
                legal_action_id=db_action.id,
                title="Processo vinculado",
                message=f"Voce foi vinculado ao processo {db_action.number} - {db_action.title}.",
            )
        return LegalActionService.get_by_id(db, db_action.id, organization_id)
    
    @staticmethod
    def update(
        db: Session,
        action_id: int,
        action_in: LegalActionUpdate,
        organization_id: int,
        user_id: Optional[int] = None,
        actor_user_id: Optional[int] = None,
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
        requested_user_ids = update_data.pop("user_ids", None)

        if "client_id" in update_data and update_data["client_id"] is not None:
            client = db.query(Client).filter(
                Client.id == update_data["client_id"],
                Client.organization_id == organization_id
            ).first()
            if not client:
                raise ValueError("Cliente não encontrado ou não pertence a esta organização")

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

        partes_data = update_data.pop("partes", None)
        movimentos_data = update_data.pop("movimentos", None)

        for field, value in update_data.items():
            setattr(db_action, field, value)

        if partes_data is not None:
            from app.models.processo_parte import ProcessoParte
            db.query(ProcessoParte).filter(ProcessoParte.legal_action_id == db_action.id).delete()
            for p in partes_data:
                db_parte = ProcessoParte(**p, legal_action_id=db_action.id)
                db.add(db_parte)
                
        if movimentos_data is not None:
            from app.models.processo_movimento import ProcessoMovimento
            db.query(ProcessoMovimento).filter(ProcessoMovimento.legal_action_id == db_action.id).delete()
            for m in movimentos_data:
                db_mov = ProcessoMovimento(**m, legal_action_id=db_action.id)
                db.add(db_mov)

        new_assigned_users = None
        new_user_ids_to_notify: set[int] = set()
        if requested_user_ids is not None:
            assigned_ids = set(requested_user_ids)
            new_assigned_users = LegalActionService._resolve_assigned_users(
                db,
                organization_id=organization_id,
                user_ids=list(assigned_ids),
            )
            current_ids = {user.id for user in db_action.assigned_users}
            new_ids = {user.id for user in new_assigned_users}
            db_action.assigned_users = new_assigned_users
            new_user_ids_to_notify = new_ids - current_ids
            if actor_user_id is not None:
                new_user_ids_to_notify.discard(actor_user_id)
        
        db.add(db_action)
        db.commit()
        db.refresh(db_action)

        if new_user_ids_to_notify:
            for target_user_id in new_user_ids_to_notify:
                NotificationService.create(
                    db,
                    user_id=target_user_id,
                    organization_id=organization_id,
                    legal_action_id=db_action.id,
                    title="Processo vinculado",
                    message=f"Voce foi vinculado ao processo {db_action.number} - {db_action.title}.",
                )
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
