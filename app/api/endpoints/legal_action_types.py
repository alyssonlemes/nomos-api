from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.database import get_db
from app.schemas.legal_action_type import (
    LegalActionTypeCreate,
    LegalActionTypeUpdate,
    LegalActionTypeResponse,
    LegalActionTypeListResponse,
)
from app.services.legal_action_type_service import LegalActionTypeService
from app.models.user import User
from app.api.deps import require_legal_actions_access

router = APIRouter()


@router.post(
    "",
    response_model=LegalActionTypeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Criar tipo de ação jurídica",
)
def create_legal_action_type(
    data_in: LegalActionTypeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_legal_actions_access),
):
    """Cria um novo tipo de ação jurídica (catálogo)."""
    existing = LegalActionTypeService.get_by_code(db, data_in.code.strip().lower())
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Já existe um tipo com este código",
        )
    obj = LegalActionTypeService.create(db, data_in)
    return obj


@router.get(
    "",
    response_model=LegalActionTypeListResponse,
    summary="Listar tipos de ação jurídica",
)
def list_legal_action_types(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    search: Optional[str] = Query(None, description="Buscar por nome ou código"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_legal_actions_access),
):
    """Lista todos os tipos de ação jurídica com paginação."""
    items, total = LegalActionTypeService.get_all(db, skip=skip, limit=limit, search=search)
    return LegalActionTypeListResponse(total=total, legal_action_types=items)


@router.get(
    "/{type_id}",
    response_model=LegalActionTypeResponse,
    summary="Obter tipo de ação jurídica",
)
def get_legal_action_type(
    type_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_legal_actions_access),
):
    """Retorna um tipo de ação jurídica pelo ID."""
    obj = LegalActionTypeService.get_by_id(db, type_id)
    if not obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tipo de ação jurídica não encontrado",
        )
    return obj


@router.put(
    "/{type_id}",
    response_model=LegalActionTypeResponse,
    summary="Atualizar tipo de ação jurídica",
)
def update_legal_action_type(
    type_id: int,
    data_in: LegalActionTypeUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_legal_actions_access),
):
    """Atualiza um tipo de ação jurídica."""
    if data_in.code is not None:
        existing = LegalActionTypeService.get_by_code(db, data_in.code.strip().lower())
        if existing and existing.id != type_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Já existe outro tipo com este código",
            )
    obj = LegalActionTypeService.update(db, type_id, data_in)
    if not obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tipo de ação jurídica não encontrado",
        )
    return obj


@router.delete(
    "/{type_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Deletar tipo de ação jurídica",
)
def delete_legal_action_type(
    type_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_legal_actions_access),
):
    """Remove um tipo. Falha se houver ações jurídicas usando este tipo."""
    obj = LegalActionTypeService.get_by_id(db, type_id)
    if not obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tipo de ação jurídica não encontrado",
        )
    try:
        LegalActionTypeService.delete(db, type_id)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Não é possível excluir: existem ações jurídicas vinculadas a este tipo",
        )
