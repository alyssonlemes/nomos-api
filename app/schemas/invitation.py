from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime
from enum import Enum

class InvitationStatus(str, Enum):
    """Status de um convite"""
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"

class InvitationRole(str, Enum):
    """Papéis possíveis para um convite"""
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"
    ASSISTANT = "assistant"  # Acesso a tudo exceto processos e jurimetria

class InvitationBase(BaseModel):
    """Schema base para Invitation"""
    email: EmailStr

class InvitationCreate(InvitationBase):
    """Schema para criar convite"""
    role: Optional[InvitationRole] = Field(None, description="Papel legado, usado quando profile_id não é enviado")
    profile_id: Optional[int] = Field(None, description="Perfil de acesso que o convidado receberá")

class InvitationAccept(BaseModel):
    """Schema para aceitar convite"""
    invitation_id: int

class InvitationResponse(InvitationBase):
    """Schema de resposta para Invitation"""
    id: int
    organization_id: int
    role: Optional[str] = None
    profile_id: Optional[int] = None
    status: InvitationStatus
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class InvitationDetailResponse(InvitationBase):
    """Schema detalhado de Invitation com informações da organização"""
    id: int
    organization_id: int
    role: Optional[str] = None
    profile_id: Optional[int] = None
    organization_name: Optional[str] = None
    invited_by_email: Optional[str] = None
    status: InvitationStatus
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class InvitationListResponse(BaseModel):
    """Schema para lista de convites"""
    total: int
    invitations: list[InvitationDetailResponse]
