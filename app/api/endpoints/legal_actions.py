from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.legal_action import (
    LegalActionCreate, LegalActionUpdate, LegalActionResponse, LegalActionListResponse,
    LegalActionDetailResponse, PartyCreate, PartyUpdate, PartyResponse,
    CaseMovementCreate, CaseMovementUpdate, CaseMovementResponse,
    DeadlineCreate, DeadlineUpdate, DeadlineResponse, LegalStatus
)
from app.services.legal_action_service import (
    LegalActionService, PartyService, CaseMovementService, DeadlineService
)
from app.models.user import User
from app.api.deps import get_current_active_user

router = APIRouter()


# ========== LEGAL ACTIONS ==========

@router.post(
    "",
    response_model=LegalActionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Criar nova ação jurídica"
)
def create_legal_action(
    action_in: LegalActionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Cria uma nova ação jurídica/processo
    
    - **number**: Número único do processo
    - **title**: Título da ação
    - **action_type**: Tipo (civil, trabalhista, criminal, etc)
    - **client_id**: ID do cliente envolvido
    """
    # Verificar se número já existe
    if LegalActionService.get_by_number(db, number=action_in.number, organization_id=current_user.organization_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ação jurídica com este número já existe"
        )
    
    action = LegalActionService.create(db=db, action_in=action_in, organization_id=current_user.organization_id, user_id=current_user.id)
    return action


@router.get(
    "",
    response_model=LegalActionListResponse,
    summary="Listar ações jurídicas"
)
def list_legal_actions(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    legal_status: Optional[LegalStatus] = Query(None, description="Filtrar por status jurídico"),
    client_id: Optional[int] = Query(None, description="Filtrar por cliente"),
    search: Optional[str] = Query(None, description="Buscar por número ou título"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Lista todas as ações jurídicas do usuário com filtros
    """
    actions, total = LegalActionService.get_all(
        db,
        organization_id=current_user.organization_id,
        skip=skip,
        limit=limit,
        legal_status=legal_status,
        client_id=client_id,
        search=search
    )
    
    return LegalActionListResponse(total=total, legal_actions=actions)


@router.get(
    "/{action_id}",
    response_model=LegalActionDetailResponse,
    summary="Obter ação jurídica com detalhes"
)
def get_legal_action(
    action_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Retorna uma ação jurídica com todas as partes, movimentações e prazos
    """
    action = LegalActionService.get_by_id(db, action_id=action_id, organization_id=current_user.organization_id)
    
    if not action:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ação jurídica não encontrada"
        )
    
    return action


@router.put(
    "/{action_id}",
    response_model=LegalActionResponse,
    summary="Atualizar ação jurídica"
)
def update_legal_action(
    action_id: int,
    action_in: LegalActionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Atualiza uma ação jurídica existente
    """
    action = LegalActionService.update(
        db,
        action_id=action_id,
        action_in=action_in,
        organization_id=current_user.organization_id
    )
    
    if not action:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ação jurídica não encontrada"
        )
    
    return action


@router.delete(
    "/{action_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Deletar ação jurídica"
)
def delete_legal_action(
    action_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Deleta uma ação jurídica
    """
    action = LegalActionService.delete(db, action_id=action_id, organization_id=current_user.organization_id)
    
    if not action:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ação jurídica não encontrada"
        )


@router.get(
    "/{action_id}/statistics",
    summary="Estatísticas de uma ação"
)
def get_action_statistics(
    action_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Retorna estatísticas de uma ação jurídica específica
    """
    action = LegalActionService.get_by_id(db, action_id=action_id, organization_id=current_user.organization_id)
    
    if not action:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ação jurídica não encontrada"
        )
    
    return {
        "total_parties": len(action.parties),
        "total_movements": len(action.movements),
        "total_deadlines": len(action.deadlines),
        "pending_deadlines": sum(1 for d in action.deadlines if d.status.value == "pending")
    }


# ========== PARTIES ==========

@router.post(
    "/{action_id}/parties",
    response_model=PartyResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Adicionar parte ao processo"
)
def add_party(
    action_id: int,
    party_in: PartyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Adiciona uma parte (autor, réu, etc) ao processo
    """
    action = LegalActionService.get_by_id(db, action_id=action_id, organization_id=current_user.organization_id)
    if not action:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ação não encontrada")
    
    party = PartyService.create(db=db, party_in=party_in, action_id=action_id)
    return party


@router.put(
    "/{action_id}/parties/{party_id}",
    response_model=PartyResponse,
    summary="Atualizar parte"
)
def update_party(
    action_id: int,
    party_id: int,
    party_in: PartyUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Atualiza uma parte do processo
    """
    action = LegalActionService.get_by_id(db, action_id=action_id, organization_id=current_user.organization_id)
    if not action:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ação não encontrada")
    
    party = PartyService.update(db, party_id=party_id, party_in=party_in, action_id=action_id)
    if not party:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Parte não encontrada")
    
    return party


@router.delete(
    "/{action_id}/parties/{party_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remover parte"
)
def delete_party(
    action_id: int,
    party_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Remove uma parte do processo
    """
    action = LegalActionService.get_by_id(db, action_id=action_id, organization_id=current_user.organization_id)
    if not action:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ação não encontrada")
    
    party = PartyService.delete(db, party_id=party_id, action_id=action_id)
    if not party:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Parte não encontrada")


# ========== MOVEMENTS ==========

@router.post(
    "/{action_id}/movements",
    response_model=CaseMovementResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar movimentação"
)
def add_movement(
    action_id: int,
    movement_in: CaseMovementCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Registra uma movimentação/andamento no processo
    
    - **movement_type**: Tipo (hearing, decision, judgment, etc)
    - **movement_date**: Data da movimentação
    """
    action = LegalActionService.get_by_id(db, action_id=action_id, organization_id=current_user.organization_id)
    if not action:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ação não encontrada")
    
    movement = CaseMovementService.create(db=db, movement_in=movement_in, action_id=action_id)
    return movement


@router.put(
    "/{action_id}/movements/{movement_id}",
    response_model=CaseMovementResponse,
    summary="Atualizar movimentação"
)
def update_movement(
    action_id: int,
    movement_id: int,
    movement_in: CaseMovementUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Atualiza uma movimentação do processo
    """
    action = LegalActionService.get_by_id(db, action_id=action_id, organization_id=current_user.organization_id)
    if not action:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ação não encontrada")
    
    movement = CaseMovementService.update(
        db, movement_id=movement_id, movement_in=movement_in, action_id=action_id
    )
    if not movement:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Movimentação não encontrada")
    
    return movement


@router.delete(
    "/{action_id}/movements/{movement_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Deletar movimentação"
)
def delete_movement(
    action_id: int,
    movement_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Deleta uma movimentação
    """
    action = LegalActionService.get_by_id(db, action_id=action_id, organization_id=current_user.organization_id)
    if not action:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ação não encontrada")
    
    movement = CaseMovementService.delete(db, movement_id=movement_id, action_id=action_id)
    if not movement:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Movimentação não encontrada")


# ========== DEADLINES ==========

@router.post(
    "/{action_id}/deadlines",
    response_model=DeadlineResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Criar prazo"
)
def add_deadline(
    action_id: int,
    deadline_in: DeadlineCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Cria um prazo para o processo
    
    - **deadline_type**: Tipo (moção, apelação, contestação, etc)
    - **due_date**: Data de vencimento
    """
    action = LegalActionService.get_by_id(db, action_id=action_id, organization_id=current_user.organization_id)
    if not action:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ação não encontrada")
    
    deadline = DeadlineService.create(db=db, deadline_in=deadline_in, action_id=action_id)
    return deadline


@router.put(
    "/{action_id}/deadlines/{deadline_id}",
    response_model=DeadlineResponse,
    summary="Atualizar prazo"
)
def update_deadline(
    action_id: int,
    deadline_id: int,
    deadline_in: DeadlineUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Atualiza um prazo
    """
    action = LegalActionService.get_by_id(db, action_id=action_id, organization_id=current_user.organization_id)
    if not action:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ação não encontrada")
    
    deadline = DeadlineService.update(
        db, deadline_id=deadline_id, deadline_in=deadline_in, action_id=action_id
    )
    if not deadline:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prazo não encontrado")
    
    return deadline


@router.delete(
    "/{action_id}/deadlines/{deadline_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Deletar prazo"
)
def delete_deadline(
    action_id: int,
    deadline_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Deleta um prazo
    """
    action = LegalActionService.get_by_id(db, action_id=action_id, organization_id=current_user.organization_id)
    if not action:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ação não encontrada")
    
    deadline = DeadlineService.delete(db, deadline_id=deadline_id, action_id=action_id)
    if not deadline:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prazo não encontrado")


@router.get(
    "/user/pending-deadlines",
    response_model=list[DeadlineResponse],
    summary="Prazos pendentes"
)
def get_pending_deadlines(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Retorna todos os prazos pendentes do usuário, ordenados por data
    """
    deadlines = DeadlineService.get_pending_deadlines(db, organization_id=current_user.organization_id)
    return deadlines


@router.get(
    "/user/overdue-deadlines",
    response_model=list[DeadlineResponse],
    summary="Prazos vencidos"
)
def get_overdue_deadlines(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Retorna todos os prazos vencidos do usuário
    """
    deadlines = DeadlineService.get_overdue_deadlines(db, organization_id=current_user.organization_id)
    return deadlines
