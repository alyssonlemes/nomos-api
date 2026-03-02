from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.database import get_db
from app.schemas.legal_action_status import (
    LegalActionStatusCreate,
    LegalActionStatusUpdate,
    LegalActionStatusResponse,
    LegalActionStatusListResponse,
)
from app.services.legal_action_status_service import LegalActionStatusService
from app.models.user import User
from app.api.deps import require_legal_actions_access

router = APIRouter()


@router.post(
    "",
    response_model=LegalActionStatusResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Criar status jurídico de ação",
)
def create_legal_action_status(
    data_in: LegalActionStatusCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_legal_actions_access),
):
    existing = LegalActionStatusService.get_by_code(db, data_in.code.strip().lower())
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Já existe um status com este código",
        )
    try:
        obj = LegalActionStatusService.create(db, data_in)
        if obj is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Código já existe ou é inválido. Use GET /legal-action-statuses para listar os códigos existentes.",
            )
        return obj
    except IntegrityError as e:
        db.rollback()
        msg = str(e.orig) if e.orig else str(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Erro de restrição no banco. Pode ser código duplicado — use GET /legal-action-statuses "
                "para ver os códigos já existentes (ex.: pre_trial, filing, litigation). "
                f"Detalhe: {msg}"
            ),
        )


@router.get(
    "",
    response_model=LegalActionStatusListResponse,
    summary="Listar status jurídicos de ação",
)
def list_legal_action_statuses(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    search: Optional[str] = Query(None, description="Buscar por nome ou código"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_legal_actions_access),
):
    items, total = LegalActionStatusService.get_all(db, skip=skip, limit=limit, search=search)
    return LegalActionStatusListResponse(total=total, legal_action_statuses=items)


@router.get(
    "/{status_id}",
    response_model=LegalActionStatusResponse,
    summary="Obter status jurídico de ação",
)
def get_legal_action_status(
    status_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_legal_actions_access),
):
    obj = LegalActionStatusService.get_by_id(db, status_id)
    if not obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Status jurídico de ação não encontrado",
        )
    return obj


@router.put(
    "/{status_id}",
    response_model=LegalActionStatusResponse,
    summary="Atualizar status jurídico de ação",
)
def update_legal_action_status(
    status_id: int,
    data_in: LegalActionStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_legal_actions_access),
):
    obj = LegalActionStatusService.update(db, status_id, data_in)
    if not obj:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Status jurídico de ação não encontrado ou código já utilizado",
        )
    return obj


@router.delete(
    "/{status_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Deletar status jurídico de ação",
)
def delete_legal_action_status(
    status_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_legal_actions_access),
):
    obj = LegalActionStatusService.get_by_id(db, status_id)
    if not obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Status jurídico de ação não encontrado",
        )
    try:
        LegalActionStatusService.delete(db, status_id)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Não é possível excluir: existem ações jurídicas utilizando este status",
        )

