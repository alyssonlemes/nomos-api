from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.api.deps import get_db, get_current_active_user, get_user_organization
from app.schemas.activity import (
    ActivityCreate,
    ActivityUpdate,
    ActivityResponse,
    ActivityListResponse,
    ActivityKanbanResponse,
    CommentCreateRequest,
    ActivityStatusUpdateRequest,
    ActivityColumnCreate,
    ActivityColumnResponse,
)
from app.models.activity import ActivityColumn
from app.models.user import User
from app.services.activity_service import ActivityService, ActivityColumnService

router = APIRouter()


# ===== Activity Endpoints =====
@router.post("/", response_model=ActivityResponse, status_code=status.HTTP_201_CREATED)
def create_activity(
    activity_in: ActivityCreate,
    db: Session = Depends(get_db),
    organization_id: int = Depends(get_user_organization),
    current_user: User = Depends(get_current_active_user),
):
    """Create a new activity (task or event)"""
    if activity_in.organization_id != organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Você não tem permissão para criar atividades nesta organização",
        )
    try:
        return ActivityService.create(
            db,
            activity_in,
            organization_id=organization_id,
            created_by_id=current_user.id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )


@router.get("/kanban", response_model=list[ActivityKanbanResponse])
def get_activities_kanban(
    db: Session = Depends(get_db),
    organization_id: int = Depends(get_user_organization),
    current_user: User = Depends(get_current_active_user),
):
    """Get activities grouped by status for Kanban view"""
    activities = ActivityService.list_for_kanban(db, organization_id)

    # Group by status
    kanban_dict = {}
    for activity in activities:
        status = activity.status
        if status not in kanban_dict:
            kanban_dict[status] = []
        kanban_dict[status].append(ActivityResponse.from_orm(activity))

    # Return as list of kanban groups
    return [
        ActivityKanbanResponse(status=status, activities=acts)
        for status, acts in kanban_dict.items()
    ]


@router.get("/", response_model=ActivityListResponse)
def list_activities(
    status: Optional[str] = None,
    type: Optional[str] = None,
    responsible_id: Optional[int] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    organization_id: int = Depends(get_user_organization),
    current_user: User = Depends(get_current_active_user),
):
    """List activities with optional filters"""
    activities, total = ActivityService.list(
        db,
        organization_id,
        status=status,
        type=type,
        responsible_id=responsible_id,
        skip=skip,
        limit=limit,
    )

    return ActivityListResponse(
        total=total,
        activities=[ActivityResponse.from_orm(a) for a in activities],
    )


@router.get("/{activity_id}", response_model=ActivityResponse)
def get_activity(
    activity_id: int,
    db: Session = Depends(get_db),
    organization_id: int = Depends(get_user_organization),
    current_user: User = Depends(get_current_active_user),
):
    """Get activity details"""
    activity = ActivityService.get_by_id(db, activity_id, organization_id)
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")
    return activity


@router.patch("/{activity_id}", response_model=ActivityResponse)
def update_activity(
    activity_id: int,
    activity_in: ActivityUpdate,
    db: Session = Depends(get_db),
    organization_id: int = Depends(get_user_organization),
    current_user: User = Depends(get_current_active_user),
):
    """Update an activity"""
    try:
        activity = ActivityService.update(
            db, activity_id, organization_id, activity_in, current_user.id
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")
    return activity


@router.post("/{activity_id}/move", response_model=ActivityResponse)
def move_activity(
    activity_id: int,
    status_update: ActivityStatusUpdateRequest,
    db: Session = Depends(get_db),
    organization_id: int = Depends(get_user_organization),
    current_user: User = Depends(get_current_active_user),
):
    """Move activity to new status (drag-drop in Kanban)"""
    activity = ActivityService.move(db, activity_id, organization_id, status_update, current_user.id)
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")
    return activity


@router.delete("/{activity_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_activity(
    activity_id: int,
    db: Session = Depends(get_db),
    organization_id: int = Depends(get_user_organization),
    current_user: User = Depends(get_current_active_user),
):
    """Delete an activity"""
    activity = ActivityService.delete(db, activity_id, organization_id)
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")


# ===== Comments =====
@router.post("/{activity_id}/comments", status_code=status.HTTP_201_CREATED)
def add_comment(
    activity_id: int,
    comment_in: CommentCreateRequest,
    db: Session = Depends(get_db),
    organization_id: int = Depends(get_user_organization),
    current_user: User = Depends(get_current_active_user),
):
    """Add a comment to an activity"""
    comment = ActivityService.add_comment(
        db, activity_id, organization_id, current_user.id, comment_in.content
    )
    if not comment:
        raise HTTPException(status_code=404, detail="Activity not found")
    return comment


@router.get("/{activity_id}/comments")
def get_comments(
    activity_id: int,
    db: Session = Depends(get_db),
    organization_id: int = Depends(get_user_organization),
    current_user: User = Depends(get_current_active_user),
):
    """Get all comments for an activity"""
    comments = ActivityService.list_comments(db, activity_id, organization_id)
    if comments is None:
        raise HTTPException(status_code=404, detail="Activity not found")
    return comments


# ===== Activity Columns (Kanban Customization) =====
@router.post("/columns/create", response_model=ActivityColumnResponse, status_code=status.HTTP_201_CREATED)
def create_activity_column(
    column_in: ActivityColumnCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Create a custom Kanban column (admin only)"""
    # Validação multi-tenant: user só pode criar colunas em sua própria organização
    if current_user.organization_id != column_in.organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Você não tem permissão para criar colunas nesta organização",
        )

    return ActivityColumnService.create(db, column_in)


@router.get("/columns/list", response_model=list[ActivityColumnResponse])
def list_activity_columns(
    organization_id: int = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """List all Kanban columns for organization"""
    # Validação multi-tenant: user só pode listar colunas de sua própria organização
    if current_user.organization_id != organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Você não tem permissão para acessar colunas desta organização",
        )

    return ActivityColumnService.list(db, organization_id)


@router.patch("/columns/{column_id}", response_model=ActivityColumnResponse)
def update_activity_column(
    column_id: int,
    column_in: ActivityColumnCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Update a Kanban column"""
    # Validação multi-tenant
    if current_user.organization_id != column_in.organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Você não tem permissão para atualizar colunas nesta organização",
        )
    column = db.query(ActivityColumn).filter(ActivityColumn.id == column_id).first()
    if not column:
        raise HTTPException(status_code=404, detail="Column not found")

    if column.organization_id != current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Você não tem permissão para atualizar esta coluna",
        )

    updated = ActivityColumnService.update(db, column_id, column_in)
    if not updated:
        raise HTTPException(status_code=404, detail="Column not found")
    return updated


@router.delete("/columns/{column_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_activity_column(
    column_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Delete a Kanban column"""
    column = db.query(ActivityColumn).filter(ActivityColumn.id == column_id).first()
    if not column:
        raise HTTPException(status_code=404, detail="Column not found")

    # Validação multi-tenant
    if column.organization_id != current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Você não tem permissão para deletar esta coluna",
        )

    # Não permite deletar colunas padrão
    if column.is_default:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Não é possível deletar colunas padrão",
        )

    ActivityColumnService.delete(db, column_id)
