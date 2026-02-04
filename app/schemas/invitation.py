from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime
from enum import Enum


class InvitationStatus(str, Enum):
    """Status de um convite"""
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


# ========== Base Schemas ==========

class InvitationBase(BaseModel):
    """Schema base para Invitation"""
    email: EmailStr


# ========== Request Schemas ==========

class InvitationCreate(InvitationBase):
    """Schema para criar convite"""
    pass


class InvitationAccept(BaseModel):
    """Schema para aceitar convite"""
    invitation_id: int


# ========== Response Schemas ==========

class InvitationResponse(InvitationBase):
    """Schema de resposta para Invitation"""
    id: int
    organization_id: int
    status: InvitationStatus
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class InvitationDetailResponse(InvitationBase):
    """Schema detalhado de Invitation com informações da organização"""
    id: int
    organization_id: int
    organization_name: Optional[str] = None
    invited_by_username: Optional[str] = None
    status: InvitationStatus
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class InvitationListResponse(BaseModel):
    """Schema para lista de convites"""
    total: int
    invitations: list[InvitationDetailResponse]
