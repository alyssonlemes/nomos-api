from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class MeetingBase(BaseModel):
    title: str = Field(...)
    description: Optional[str] = None
    start_at: datetime
    end_at: datetime
    participant_ids: List[int] = Field(default_factory=list)
    requires_acceptance: bool = False


class MeetingCreate(MeetingBase):
    organization_id: int


class MeetingPreviewRequest(BaseModel):
    start_at: datetime
    end_at: datetime
    participant_ids: List[int] = Field(default_factory=list)


class ConflictingMeeting(BaseModel):
    id: int
    title: str
    start_at: datetime
    end_at: datetime
    participant_id: int


class MeetingParticipantBase(BaseModel):
    id: int
    user_id: int
    status: str
    accepted_at: Optional[datetime] = None
    reason: Optional[str] = None
    responded_by_id: Optional[int] = None


class ConflictParticipant(BaseModel):
    id: int
    full_name: Optional[str] = None
    email: Optional[str] = None


class MeetingConflictResponse(BaseModel):
    id: int
    title: str
    start_at: datetime
    end_at: datetime
    participants: List[ConflictParticipant]


class MeetingResponse(MeetingBase):
    id: int
    organization_id: int
    created_by_id: Optional[int] = None
    created_at: datetime
    requires_acceptance: bool = False
    status: str = "scheduled"

    class Config:
        from_attributes = True


class MeetingListResponse(BaseModel):
    total: int
    meetings: List[MeetingResponse]
