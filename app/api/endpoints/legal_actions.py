from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.legal_action import (
    LegalActionCreate, LegalActionUpdate, LegalActionResponse, LegalActionListResponse
)
from app.services.legal_action_service import LegalActionService
from app.models.user import User
from app.api.deps import get_current_active_user

router = APIRouter()


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
    Cria uma nova ação jurídica/processo (Etapa 3 do fluxo)
    
    Requer que o usuário tenha uma organização criada.
    
    - **number**: Número único do processo
    - **title**: Título da ação
    - **action_type_id**: ID do tipo de ação (listar em GET /legal-action-types)
    - **client_id**: ID do cliente envolvido
    """
    # Verificar se usuário tem organização
    if not current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Você precisa ter uma organização para criar ações jurídicas. Crie uma organização primeiro."
        )
    
    # Verificar se número já existe
    if LegalActionService.get_by_number(db, number=action_in.number, organization_id=current_user.organization_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ação jurídica com este número já existe"
        )
    
    action = LegalActionService.create(db=db, action_in=action_in, organization_id=current_user.organization_id, user_id=current_user.id)
    if not action:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tipo de ação jurídica (action_type_id) inválido ou não encontrado",
        )
    return action


@router.get(
    "",
    response_model=LegalActionListResponse,
    summary="Listar ações jurídicas"
)
def list_legal_actions(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    legal_status: Optional[str] = Query(None, description="Filtrar por status jurídico"),
    client_id: Optional[int] = Query(None, description="Filtrar por cliente"),
    search: Optional[str] = Query(None, description="Buscar por número ou título"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Lista todas as ações jurídicas da organização com filtros (Etapa 3 do fluxo)
    
    Requer que o usuário tenha uma organização criada.
    """
    # Verificar se usuário tem organização
    if not current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Você precisa ter uma organização para acessar ações jurídicas. Crie uma organização primeiro."
        )
    
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
    response_model=LegalActionResponse,
    summary="Obter ação jurídica"
)
def get_legal_action(
    action_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Retorna uma ação jurídica específica
    """
    # Verificar se usuário tem organização
    if not current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Você precisa ter uma organização para acessar ações jurídicas."
        )
    
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
    # Verificar se usuário tem organização
    if not current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Você precisa ter uma organização."
        )
    
    try:
        action = LegalActionService.update(
            db,
            action_id=action_id,
            action_in=action_in,
            organization_id=current_user.organization_id,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    if not action:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ação jurídica não encontrada",
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
    # Verificar se usuário tem organização
    if not current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Você precisa ter uma organização."
        )
    
    action = LegalActionService.delete(db, action_id=action_id, organization_id=current_user.organization_id)
    
    if not action:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ação jurídica não encontrada"
        )
