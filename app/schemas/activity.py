from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import datetime, date, time


# ===== Base Schemas =====
class ActivityParticipantBase(BaseModel):
    user_id: int
    role: Optional[str] = None


class ActivityCommentBase(BaseModel):
    content: str


class ActivityAttachmentBase(BaseModel):
    file_url: str
    file_name: Optional[str] = None


# ===== Response Schemas =====
class UserBasicInfo(BaseModel):
    id: int
    full_name: Optional[str] = None
    email: Optional[str] = None

    class Config:
        from_attributes = True


class ActivityParticipantResponse(ActivityParticipantBase):
    id: int
    activity_id: int
    user: Optional[UserBasicInfo] = None

    class Config:
        from_attributes = True


class ActivityCommentResponse(ActivityCommentBase):
    id: int
    activity_id: int
    author: Optional[UserBasicInfo] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ActivityAttachmentResponse(ActivityAttachmentBase):
    id: int
    activity_id: int
    uploaded_by: Optional[UserBasicInfo] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ActivityHistoryResponse(BaseModel):
    id: int
    activity_id: int
    field_changed: str
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    changed_by: Optional[UserBasicInfo] = None
    changed_at: datetime

    class Config:
        from_attributes = True


# ===== Activity Schemas =====
class ActivityBase(BaseModel):
    title: str = Field(...)
    description: Optional[str] = None
    type: str = Field(..., description="'task' or 'event'")
    responsible_id: Optional[int] = None
    priority: str = Field(default="medium", description="low, medium, high, critical")
    status: str = Field(default="todo", description="todo, in_progress, done")
    start_date: date
    end_date: date
    observations: Optional[str] = None
    
    # Event-specific
    event_time: Optional[time] = None
    location_or_link: Optional[str] = None
    
    # Task-specific
    estimated_hours: Optional[int] = None
    
    @field_validator('event_time', mode='before')
    @classmethod
    def validate_event_time(cls, v):
        """Accept empty strings and convert to None"""
        if v == "" or v is None:
            return None
        return v
    
    @field_validator('location_or_link', mode='before')
    @classmethod
    def validate_location(cls, v):
        """Accept empty strings and convert to None"""
        if v == "":
            return None
        return v


class ActivityCreate(ActivityBase):
    organization_id: int
    participant_ids: List[int] = Field(default_factory=list)


class ActivityUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    responsible_id: Optional[int] = None
    priority: Optional[str] = None
    status: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    event_time: Optional[time] = None
    location_or_link: Optional[str] = None
    estimated_hours: Optional[int] = None
    observations: Optional[str] = None


class ActivityResponse(ActivityBase):
    id: int
    organization_id: int
    created_by_id: Optional[int] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    responsible: Optional[UserBasicInfo] = None
    created_by: Optional[UserBasicInfo] = None
    participants: List[UserBasicInfo] = []
    comments: List[ActivityCommentResponse] = []
    attachments: List[ActivityAttachmentResponse] = []
    history: List[ActivityHistoryResponse] = []

    class Config:
        from_attributes = True


class ActivityListResponse(BaseModel):
    total: int
    activities: List[ActivityResponse]


class ActivityKanbanResponse(BaseModel):
    """Grouped by status/column for Kanban view"""
    status: str
    activities: List[ActivityResponse]


# ===== Activity Columns =====
class ActivityColumnBase(BaseModel):
    name: str
    status: Optional[str] = None  # Status da atividade que essa coluna representa
    order_index: int
    color: Optional[str] = None
    is_default: bool = False


class ActivityColumnCreate(ActivityColumnBase):
    organization_id: int


class ActivityColumnResponse(ActivityColumnBase):
    id: int
    organization_id: int
    created_at: datetime

    class Config:
        from_attributes = True


# ===== Comments =====
class CommentCreateRequest(BaseModel):
    content: str


# ===== Status Update / Drag-Drop =====
class ActivityStatusUpdateRequest(BaseModel):
    new_status: str = Field(..., description="todo, in_progress, done")
