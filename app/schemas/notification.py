from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime


class NotificationResponse(BaseModel):
    id: int
    title: str
    message: str
    legal_action_id: Optional[int] = None
    read_at: Optional[datetime] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class NotificationListResponse(BaseModel):
    total: int
    notifications: list[NotificationResponse]
