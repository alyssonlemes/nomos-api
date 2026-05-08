from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional
import re

from app.api.deps import get_db, get_current_user
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
from app.models.activity import (
    Activity,
    ActivityParticipant,
    ActivityComment,
    ActivityHistory,
    ActivityAttachment,
    ActivityColumn,
)
from app.models.user import User

router = APIRouter()


# ===== Helper Functions =====
def create_history_entry(
    db: Session,
    activity_id: int,
    field_changed: str,
    old_value: Optional[str],
    new_value: Optional[str],
    changed_by_id: int,
):
    """Record a change in activity history"""
    history = ActivityHistory(
        activity_id=activity_id,
        field_changed=field_changed,
        old_value=old_value,
        new_value=new_value,
        changed_by_id=changed_by_id,
    )
    db.add(history)
    db.commit()


def generate_status_key(name: str) -> str:
    """Generate a normalized technical status key from a display name."""
    key = re.sub(r"[^a-z0-9_]+", "_", name.strip().lower())
    key = re.sub(r"_+", "_", key).strip("_")
    return key or "custom"


# ===== Activity Endpoints =====
@router.post("/", response_model=ActivityResponse, status_code=status.HTTP_201_CREATED)
def create_activity(
    activity_in: ActivityCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new activity (task or event)"""
    # Create activity
    activity = Activity(
        organization_id=activity_in.organization_id,
        title=activity_in.title,
        description=activity_in.description,
        type=activity_in.type,
        responsible_id=activity_in.responsible_id,
        priority=activity_in.priority,
        status=activity_in.status,
        start_date=activity_in.start_date,
        end_date=activity_in.end_date,
        event_time=activity_in.event_time,
        location_or_link=activity_in.location_or_link,
        estimated_hours=activity_in.estimated_hours,
        observations=activity_in.observations,
        created_by_id=current_user.id,
    )
    db.add(activity)
    db.flush()

    # Add participants
    for participant_id in activity_in.participant_ids:
        participant = ActivityParticipant(
            activity_id=activity.id,
            user_id=participant_id,
        )
        db.add(participant)

    db.commit()
    db.refresh(activity)

    return activity


@router.get("/kanban", response_model=list[ActivityKanbanResponse])
def get_activities_kanban(
    organization_id: int = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get activities grouped by status for Kanban view"""
    # Get all activities for organization
    activities = (
        db.query(Activity)
        .filter(Activity.organization_id == organization_id)
        .order_by(Activity.status, Activity.created_at)
        .all()
    )

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
    organization_id: int = Query(...),
    status: Optional[str] = None,
    type: Optional[str] = None,
    responsible_id: Optional[int] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List activities with optional filters"""
    query = db.query(Activity).filter(Activity.organization_id == organization_id)

    if status:
        query = query.filter(Activity.status == status)
    if type:
        query = query.filter(Activity.type == type)
    if responsible_id:
        query = query.filter(Activity.responsible_id == responsible_id)

    total = query.count()
    activities = query.order_by(Activity.created_at.desc()).offset(skip).limit(limit).all()

    return ActivityListResponse(
        total=total,
        activities=[ActivityResponse.from_orm(a) for a in activities],
    )


@router.get("/{activity_id}", response_model=ActivityResponse)
def get_activity(
    activity_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get activity details"""
    activity = db.query(Activity).filter(Activity.id == activity_id).first()
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")
    return activity


@router.patch("/{activity_id}", response_model=ActivityResponse)
def update_activity(
    activity_id: int,
    activity_in: ActivityUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update an activity"""
    activity = db.query(Activity).filter(Activity.id == activity_id).first()
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")

    # Track changes for history
    changes = []
    
    # Update fields
    if activity_in.title is not None and activity_in.title != activity.title:
        changes.append(("title", str(activity.title), str(activity_in.title)))
        activity.title = activity_in.title
    
    if activity_in.description is not None and activity_in.description != activity.description:
        changes.append(("description", activity.description, activity_in.description))
        activity.description = activity_in.description
    
    if activity_in.status is not None and activity_in.status != activity.status:
        changes.append(("status", activity.status, activity_in.status))
        activity.status = activity_in.status
    
    if activity_in.priority is not None and activity_in.priority != activity.priority:
        changes.append(("priority", activity.priority, activity_in.priority))
        activity.priority = activity_in.priority
    
    if activity_in.responsible_id is not None and activity_in.responsible_id != activity.responsible_id:
        changes.append(("responsible_id", str(activity.responsible_id), str(activity_in.responsible_id)))
        activity.responsible_id = activity_in.responsible_id
    
    if activity_in.start_date is not None and activity_in.start_date != activity.start_date:
        changes.append(("start_date", str(activity.start_date), str(activity_in.start_date)))
        activity.start_date = activity_in.start_date
    
    if activity_in.end_date is not None and activity_in.end_date != activity.end_date:
        changes.append(("end_date", str(activity.end_date), str(activity_in.end_date)))
        activity.end_date = activity_in.end_date
    
    if activity_in.event_time is not None and activity_in.event_time != activity.event_time:
        changes.append(("event_time", str(activity.event_time), str(activity_in.event_time)))
        activity.event_time = activity_in.event_time
    
    if activity_in.location_or_link is not None and activity_in.location_or_link != activity.location_or_link:
        changes.append(("location_or_link", activity.location_or_link, activity_in.location_or_link))
        activity.location_or_link = activity_in.location_or_link
    
    if activity_in.estimated_hours is not None and activity_in.estimated_hours != activity.estimated_hours:
        changes.append(("estimated_hours", str(activity.estimated_hours), str(activity_in.estimated_hours)))
        activity.estimated_hours = activity_in.estimated_hours
    
    if activity_in.observations is not None and activity_in.observations != activity.observations:
        changes.append(("observations", activity.observations, activity_in.observations))
        activity.observations = activity_in.observations

    db.add(activity)
    db.commit()

    # Record history entries
    for field, old_val, new_val in changes:
        create_history_entry(db, activity_id, field, old_val, new_val, current_user.id)

    db.refresh(activity)
    return activity


@router.post("/{activity_id}/move", response_model=ActivityResponse)
def move_activity(
    activity_id: int,
    status_update: ActivityStatusUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Move activity to new status (drag-drop in Kanban)"""
    activity = db.query(Activity).filter(Activity.id == activity_id).first()
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")

    old_status = activity.status
    activity.status = status_update.new_status
    db.add(activity)
    db.commit()

    # Record in history
    create_history_entry(db, activity_id, "status", old_status, status_update.new_status, current_user.id)

    db.refresh(activity)
    return activity


@router.delete("/{activity_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_activity(
    activity_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete an activity"""
    activity = db.query(Activity).filter(Activity.id == activity_id).first()
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")

    db.delete(activity)
    db.commit()


# ===== Comments =====
@router.post("/{activity_id}/comments", status_code=status.HTTP_201_CREATED)
def add_comment(
    activity_id: int,
    comment_in: CommentCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Add a comment to an activity"""
    activity = db.query(Activity).filter(Activity.id == activity_id).first()
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")

    comment = ActivityComment(
        activity_id=activity_id,
        author_id=current_user.id,
        content=comment_in.content,
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)

    return comment


@router.get("/{activity_id}/comments")
def get_comments(
    activity_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get all comments for an activity"""
    activity = db.query(Activity).filter(Activity.id == activity_id).first()
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")

    comments = db.query(ActivityComment).filter(ActivityComment.activity_id == activity_id).all()
    return comments


# ===== Activity Columns (Kanban Customization) =====
@router.post("/columns/create", response_model=ActivityColumnResponse, status_code=status.HTTP_201_CREATED)
def create_activity_column(
    column_in: ActivityColumnCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a custom Kanban column (admin only)"""
    # Validação multi-tenant: user só pode criar colunas em sua própria organização
    if current_user.organization_id != column_in.organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Você não tem permissão para criar colunas nesta organização",
        )

    status_key = column_in.status or generate_status_key(column_in.name)
    base_status_key = status_key
    suffix = 2

    # Garante unicidade por organização para evitar colisões de chave técnica.
    while db.query(ActivityColumn).filter(
        ActivityColumn.organization_id == column_in.organization_id,
        ActivityColumn.status == status_key,
    ).first():
        status_key = f"{base_status_key}_{suffix}"
        suffix += 1

    column = ActivityColumn(
        organization_id=column_in.organization_id,
        name=column_in.name,
        status=status_key,
        order_index=column_in.order_index,
        color=column_in.color,
        is_default=column_in.is_default,
    )
    db.add(column)
    db.commit()
    db.refresh(column)

    return column


@router.get("/columns/list", response_model=list[ActivityColumnResponse])
def list_activity_columns(
    organization_id: int = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all Kanban columns for organization"""
    # Validação multi-tenant: user só pode listar colunas de sua própria organização
    if current_user.organization_id != organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Você não tem permissão para acessar colunas desta organização",
        )

    columns = (
        db.query(ActivityColumn)
        .filter(ActivityColumn.organization_id == organization_id)
        .order_by(ActivityColumn.order_index)
        .all()
    )
    # Se não houver colunas personalizadas, crie as colunas padrão para a organização
    if not columns:
        default_cols = [
            {"name": "A Fazer", "status": "todo", "color": "#f1f5f9", "order_index": 1, "is_default": True},
            {"name": "Em Andamento", "status": "in_progress", "color": "#dbeafe", "order_index": 2, "is_default": True},
            {"name": "Concluído", "status": "done", "color": "#dcfce7", "order_index": 3, "is_default": True},
        ]
        for c in default_cols:
            col = ActivityColumn(
                organization_id=organization_id,
                name=c["name"],
                status=c["status"],
                order_index=c["order_index"],
                color=c["color"],
                is_default=c["is_default"],
            )
            db.add(col)
        db.commit()
        columns = (
            db.query(ActivityColumn)
            .filter(ActivityColumn.organization_id == organization_id)
            .order_by(ActivityColumn.order_index)
            .all()
        )

    return columns


@router.patch("/columns/{column_id}", response_model=ActivityColumnResponse)
def update_activity_column(
    column_id: int,
    column_in: ActivityColumnCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
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

    # Validar que a coluna pertence à organização do user
    if column.organization_id != current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Você não tem permissão para atualizar esta coluna",
        )

    column.name = column_in.name
    if column_in.status:
        column.status = column_in.status
    column.order_index = column_in.order_index
    if column_in.color:
        column.color = column_in.color
    column.is_default = column_in.is_default

    db.add(column)
    db.commit()
    db.refresh(column)

    return column


@router.delete("/columns/{column_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_activity_column(
    column_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
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

    db.delete(column)
    db.commit()
