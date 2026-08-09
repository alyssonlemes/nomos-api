from typing import Optional, Tuple, List
from sqlalchemy.orm import Session
from sqlalchemy import desc
from datetime import datetime

from app.models.notification import Notification


class NotificationService:
    """Servico para notificacoes in-app."""

    @staticmethod
    def create(
        db: Session,
        *,
        user_id: int,
        organization_id: int,
        title: str,
        message: str,
        legal_action_id: Optional[int] = None,
    ) -> Notification:
        notification = Notification(
            user_id=user_id,
            organization_id=organization_id,
            legal_action_id=legal_action_id,
            title=title,
            message=message,
        )
        db.add(notification)
        db.commit()
        db.refresh(notification)
        return notification

    @staticmethod
    def list_for_user(
        db: Session,
        *,
        user_id: int,
        organization_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> Tuple[List[Notification], int]:
        query = db.query(Notification).filter(Notification.user_id == user_id)
        if organization_id is not None:
            query = query.filter(Notification.organization_id == organization_id)
        total = query.count()
        notifications = (
            query.order_by(desc(Notification.created_at))
            .offset(skip)
            .limit(limit)
            .all()
        )
        return notifications, total

    @staticmethod
    def mark_as_read(
        db: Session,
        *,
        notification_id: int,
        user_id: int,
        organization_id: Optional[int] = None,
    ) -> Optional[Notification]:
        query = db.query(Notification).filter(
            Notification.id == notification_id,
            Notification.user_id == user_id
        )
        if organization_id is not None:
            query = query.filter(Notification.organization_id == organization_id)
        notification = query.first()
        if not notification:
            return None
        if notification.read_at is None:
            notification.read_at = datetime.utcnow()
            db.add(notification)
            db.commit()
            db.refresh(notification)
        return notification

    @staticmethod
    def list_for_user_since_id(
        db: Session,
        *,
        user_id: int,
        since_id: int,
        organization_id: Optional[int] = None,
        limit: int = 100,
    ) -> List[Notification]:
        query = db.query(Notification).filter(
            Notification.user_id == user_id,
            Notification.id > since_id
        )
        if organization_id is not None:
            query = query.filter(Notification.organization_id == organization_id)
        return (
            query.order_by(Notification.id.asc())
            .limit(limit)
            .all()
        )
