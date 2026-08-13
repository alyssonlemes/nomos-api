from __future__ import annotations

from typing import Optional, Tuple, List
import re

from sqlalchemy.orm import Session

from app.models.activity import (
    Activity,
    ActivityParticipant,
    ActivityComment,
    ActivityHistory,
    ActivityColumn,
)
from app.models.user import User
from app.schemas.activity import ActivityCreate, ActivityUpdate, ActivityStatusUpdateRequest, ActivityColumnCreate


class ActivityService:
    @staticmethod
    def get_by_id(db: Session, activity_id: int, organization_id: int) -> Optional[Activity]:
        return (
            db.query(Activity)
            .filter(Activity.id == activity_id, Activity.organization_id == organization_id)
            .first()
        )

    @staticmethod
    def _validate_users_belong_to_org(
        db: Session,
        organization_id: int,
        responsible_id: Optional[int],
        participant_ids: list[int],
    ) -> None:
        user_ids = set(participant_ids)
        if responsible_id is not None:
            user_ids.add(responsible_id)
        if not user_ids:
            return

        user_ids_list = list(user_ids)

        valid_count = (
            db.query(User)
            .filter(User.id.in_(user_ids_list), User.organization_id == organization_id)
            .count()
        )
        if valid_count != len(user_ids_list):
            raise ValueError("responsible_id/participant_ids devem pertencer à mesma organização")

    @staticmethod
    def list(
        db: Session,
        organization_id: int,
        status: Optional[str] = None,
        type: Optional[str] = None,
        responsible_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[Activity], int]:
        query = db.query(Activity).filter(Activity.organization_id == organization_id)

        if status:
            query = query.filter(Activity.status == status)
        if type:
            query = query.filter(Activity.type == type)
        if responsible_id:
            query = query.filter(Activity.responsible_id == responsible_id)

        total = query.count()
        activities = (
            query.order_by(Activity.created_at.desc()).offset(skip).limit(limit).all()
        )
        return activities, total

    @staticmethod
    def list_for_kanban(db: Session, organization_id: int) -> List[Activity]:
        return (
            db.query(Activity)
            .filter(Activity.organization_id == organization_id)
            .order_by(Activity.status, Activity.created_at)
            .all()
        )

    @staticmethod
    def create(
        db: Session,
        activity_in: ActivityCreate,
        organization_id: int,
        created_by_id: int,
    ) -> Activity:
        ActivityService._validate_users_belong_to_org(
            db,
            organization_id=organization_id,
            responsible_id=activity_in.responsible_id,
            participant_ids=list(activity_in.participant_ids),
        )
        activity = Activity(
            organization_id=organization_id,
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
            created_by_id=created_by_id,
        )
        db.add(activity)
        db.flush()

        for participant_id in activity_in.participant_ids:
            db.add(ActivityParticipant(activity_id=activity.id, user_id=participant_id))

        db.commit()
        db.refresh(activity)
        return activity

    @staticmethod
    def _create_history_entry(
        db: Session,
        activity_id: int,
        field_changed: str,
        old_value: Optional[str],
        new_value: Optional[str],
        changed_by_id: int,
    ) -> None:
        history = ActivityHistory(
            activity_id=activity_id,
            field_changed=field_changed,
            old_value=old_value,
            new_value=new_value,
            changed_by_id=changed_by_id,
        )
        db.add(history)
        db.commit()

    @staticmethod
    def update(
        db: Session,
        activity_id: int,
        organization_id: int,
        activity_in: ActivityUpdate,
        changed_by_id: int,
    ) -> Optional[Activity]:
        activity = ActivityService.get_by_id(db, activity_id, organization_id)
        if not activity:
            return None

        changes: list[tuple[str, Optional[str], Optional[str]]] = []

        if activity_in.title is not None and activity_in.title != activity.title:
            changes.append(("title", str(activity.title), str(activity_in.title)))
            activity.title = activity_in.title

        if (
            activity_in.description is not None
            and activity_in.description != activity.description
        ):
            changes.append(("description", activity.description, activity_in.description))
            activity.description = activity_in.description

        if activity_in.status is not None and activity_in.status != activity.status:
            changes.append(("status", activity.status, activity_in.status))
            activity.status = activity_in.status

        if (
            activity_in.priority is not None
            and activity_in.priority != activity.priority
        ):
            changes.append(("priority", activity.priority, activity_in.priority))
            activity.priority = activity_in.priority

        if (
            activity_in.responsible_id is not None
            and activity_in.responsible_id != activity.responsible_id
        ):
            ActivityService._validate_users_belong_to_org(
                db,
                organization_id=organization_id,
                responsible_id=activity_in.responsible_id,
                participant_ids=[],
            )
            changes.append(
                (
                    "responsible_id",
                    str(activity.responsible_id),
                    str(activity_in.responsible_id),
                )
            )
            activity.responsible_id = activity_in.responsible_id

        if (
            activity_in.start_date is not None
            and activity_in.start_date != activity.start_date
        ):
            changes.append(("start_date", str(activity.start_date), str(activity_in.start_date)))
            activity.start_date = activity_in.start_date

        if activity_in.end_date is not None and activity_in.end_date != activity.end_date:
            changes.append(("end_date", str(activity.end_date), str(activity_in.end_date)))
            activity.end_date = activity_in.end_date

        if (
            activity_in.event_time is not None
            and activity_in.event_time != activity.event_time
        ):
            changes.append(("event_time", str(activity.event_time), str(activity_in.event_time)))
            activity.event_time = activity_in.event_time

        if (
            activity_in.location_or_link is not None
            and activity_in.location_or_link != activity.location_or_link
        ):
            changes.append(
                ("location_or_link", activity.location_or_link, activity_in.location_or_link)
            )
            activity.location_or_link = activity_in.location_or_link

        if (
            activity_in.estimated_hours is not None
            and activity_in.estimated_hours != activity.estimated_hours
        ):
            changes.append(
                (
                    "estimated_hours",
                    str(activity.estimated_hours),
                    str(activity_in.estimated_hours),
                )
            )
            activity.estimated_hours = activity_in.estimated_hours

        if (
            activity_in.observations is not None
            and activity_in.observations != activity.observations
        ):
            changes.append(("observations", activity.observations, activity_in.observations))
            activity.observations = activity_in.observations

        db.add(activity)
        db.commit()

        for field, old_val, new_val in changes:
            ActivityService._create_history_entry(
                db, activity_id, field, old_val, new_val, changed_by_id
            )

        db.refresh(activity)
        return activity

    @staticmethod
    def move(
        db: Session,
        activity_id: int,
        organization_id: int,
        status_update: ActivityStatusUpdateRequest,
        changed_by_id: int,
    ) -> Optional[Activity]:
        activity = ActivityService.get_by_id(db, activity_id, organization_id)
        if not activity:
            return None

        old_status = activity.status
        activity.status = status_update.new_status
        db.add(activity)
        db.commit()

        ActivityService._create_history_entry(
            db, activity_id, "status", old_status, status_update.new_status, changed_by_id
        )

        db.refresh(activity)
        return activity

    @staticmethod
    def delete(db: Session, activity_id: int, organization_id: int) -> Optional[Activity]:
        activity = ActivityService.get_by_id(db, activity_id, organization_id)
        if not activity:
            return None

        db.delete(activity)
        db.commit()
        return activity

    @staticmethod
    def add_comment(
        db: Session,
        activity_id: int,
        organization_id: int,
        author_id: int,
        content: str,
    ) -> Optional[ActivityComment]:
        activity = ActivityService.get_by_id(db, activity_id, organization_id)
        if not activity:
            return None

        comment = ActivityComment(activity_id=activity_id, author_id=author_id, content=content)
        db.add(comment)
        db.commit()
        db.refresh(comment)
        return comment

    @staticmethod
    def list_comments(db: Session, activity_id: int, organization_id: int) -> Optional[list[ActivityComment]]:
        activity = ActivityService.get_by_id(db, activity_id, organization_id)
        if not activity:
            return None

        return (
            db.query(ActivityComment)
            .filter(ActivityComment.activity_id == activity_id)
            .all()
        )


class ActivityColumnService:
    @staticmethod
    def _generate_status_key(name: str) -> str:
        key = re.sub(r"[^a-z0-9_]+", "_", name.strip().lower())
        key = re.sub(r"_+", "_", key).strip("_")
        return key or "custom"

    @staticmethod
    def create(db: Session, column_in: ActivityColumnCreate) -> ActivityColumn:
        status_key = column_in.status or ActivityColumnService._generate_status_key(column_in.name)
        base_status_key = status_key
        suffix = 2

        while (
            db.query(ActivityColumn)
            .filter(
                ActivityColumn.organization_id == column_in.organization_id,
                ActivityColumn.status == status_key,
            )
            .first()
        ):
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

    @staticmethod
    def list(db: Session, organization_id: int) -> list[ActivityColumn]:
        columns = (
            db.query(ActivityColumn)
            .filter(ActivityColumn.organization_id == organization_id)
            .order_by(ActivityColumn.order_index)
            .all()
        )

        if columns:
            return columns

        default_cols = [
            {
                "name": "A Fazer",
                "status": "todo",
                "color": "#f1f5f9",
                "order_index": 1,
                "is_default": True,
            },
            {
                "name": "Em Andamento",
                "status": "in_progress",
                "color": "#dbeafe",
                "order_index": 2,
                "is_default": True,
            },
            {
                "name": "Concluído",
                "status": "done",
                "color": "#dcfce7",
                "order_index": 3,
                "is_default": True,
            },
        ]

        for c in default_cols:
            db.add(
                ActivityColumn(
                    organization_id=organization_id,
                    name=c["name"],
                    status=c["status"],
                    order_index=c["order_index"],
                    color=c["color"],
                    is_default=c["is_default"],
                )
            )
        db.commit()

        return (
            db.query(ActivityColumn)
            .filter(ActivityColumn.organization_id == organization_id)
            .order_by(ActivityColumn.order_index)
            .all()
        )

    @staticmethod
    def update(db: Session, column_id: int, column_in: ActivityColumnCreate) -> Optional[ActivityColumn]:
        column = db.query(ActivityColumn).filter(ActivityColumn.id == column_id).first()
        if not column:
            return None

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

    @staticmethod
    def delete(db: Session, column_id: int) -> Optional[ActivityColumn]:
        column = db.query(ActivityColumn).filter(ActivityColumn.id == column_id).first()
        if not column:
            return None

        db.delete(column)
        db.commit()
        return column
