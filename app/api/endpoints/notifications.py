import asyncio

from fastapi import APIRouter, Depends, HTTPException, Query, status, WebSocket, WebSocketDisconnect
from fastapi.encoders import jsonable_encoder
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.database import get_db
from app.api.deps import get_current_active_user
from app.models.user import User
from app.schemas.notification import NotificationListResponse, NotificationResponse
from app.services.notification_service import NotificationService
from app.services.user_service import UserService
from app.core.config import settings
from app.database import SessionLocal

router = APIRouter()


def get_user_from_token(db: Session, token: str) -> User | None:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: str | None = payload.get("sub")
        if not email:
            return None
    except JWTError:
        return None

    return UserService.get_by_email(db, email=email)


@router.get("", response_model=NotificationListResponse, summary="Listar notificacoes")
def list_notifications(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    notifications, total = NotificationService.list_for_user(
        db,
        user_id=current_user.id,
        skip=skip,
        limit=limit,
    )
    return NotificationListResponse(total=total, notifications=notifications)


@router.patch(
    "/{notification_id}/read",
    response_model=NotificationResponse,
    summary="Marcar notificacao como lida",
)
def mark_notification_as_read(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    notification = NotificationService.mark_as_read(
        db,
        notification_id=notification_id,
        user_id=current_user.id,
    )
    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notificacao nao encontrada",
        )
    return notification


@router.websocket("/ws")
async def notifications_ws(websocket: WebSocket):
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=1008)
        return

    db = SessionLocal()
    try:
        user = get_user_from_token(db, token)
    finally:
        db.close()

    if not user:
        await websocket.close(code=1008)
        return

    await websocket.accept()

    last_id = 0
    try:
        db = SessionLocal()
        try:
            items, _ = NotificationService.list_for_user(db, user_id=user.id, skip=0, limit=5)
            if items:
                last_id = max(item.id for item in items)
            await websocket.send_json(
                {
                    "type": "snapshot",
                    "notifications": jsonable_encoder(items),
                }
            )
        finally:
            db.close()

        while True:
            await asyncio.sleep(5)
            db = SessionLocal()
            try:
                new_items = NotificationService.list_for_user_since_id(
                    db,
                    user_id=user.id,
                    since_id=last_id,
                    limit=50,
                )
                if new_items:
                    last_id = new_items[-1].id
                    await websocket.send_json(
                        {
                            "type": "new",
                            "notifications": jsonable_encoder(new_items),
                        }
                    )
            finally:
                db.close()
    except WebSocketDisconnect:
        return
