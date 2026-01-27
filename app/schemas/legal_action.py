from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import Optional
from datetime import datetime, date
from enum import Enum


# ========== Enums ==========

class LegalActionType(str, Enum):
    """Tipos de ações jurídicas"""
    LABOR = "labor"
    CIVIL = "civil"
    CRIMINAL = "criminal"
    ADMINISTRATIVE = "admin"
    TAX = "tax"
    COMMERCIAL = "commercial"
    FAMILY = "family"
    REAL_ESTATE = "real_estate"
    OTHER = "other"


class LegalStatus(str, Enum):
    """Status jurídico do processo"""
    PRE_TRIAL = "pre_trial"
    FILING = "filing"
    LITIGATION = "litigation"
    EXECUTION = "execution"
    APPEAL = "appeal"
    FINALIZED = "finalized"
    ARCHIVED = "archived"


class PartyType(str, Enum):
    """Tipo de parte"""
    PLAINTIFF = "plaintiff"
    DEFENDANT = "defendant"
    THIRD_PARTY = "third_party"
    APPELLANT = "appellant"
    APPELLEE = "appellee"


class MovementType(str, Enum):
    """Tipo de movimentação"""
    FILING = "filing"
    HEARING = "hearing"
    DECISION = "decision"
    APPEAL = "appeal"
    JUDGMENT = "judgment"
    COMPLIANCE = "compliance"
    NOTIFICATION = "notification"
    OTHER = "other"


class DeadlineStatus(str, Enum):
    """Status do prazo"""
    PENDING = "pending"
    COMPLETED = "completed"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"


# ========== Party Schemas ==========

class PartyBase(BaseModel):
    """Schema base para Party"""
    name: str = Field(..., min_length=3)
    party_type: PartyType
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    document: Optional[str] = None
    legal_representative: Optional[str] = None


class PartyCreate(PartyBase):
    """Schema para criação de parte"""
    pass


class PartyUpdate(BaseModel):
    """Schema para atualização de parte"""
    name: Optional[str] = Field(None, min_length=3)
    party_type: Optional[PartyType] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    document: Optional[str] = None
    legal_representative: Optional[str] = None


class PartyResponse(PartyBase):
    """Schema de resposta para Party"""
    id: int
    legal_action_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# ========== CaseMovement Schemas ==========

class CaseMovementBase(BaseModel):
    """Schema base para CaseMovement"""
    title: str = Field(..., min_length=3)
    description: Optional[str] = None
    movement_type: MovementType
    movement_date: date
    notification_date: Optional[date] = None
    source: Optional[str] = None


class CaseMovementCreate(CaseMovementBase):
    """Schema para criação de movimentação"""
    pass


class CaseMovementUpdate(BaseModel):
    """Schema para atualização de movimentação"""
    title: Optional[str] = Field(None, min_length=3)
    description: Optional[str] = None
    movement_type: Optional[MovementType] = None
    movement_date: Optional[date] = None
    notification_date: Optional[date] = None
    source: Optional[str] = None


class CaseMovementResponse(CaseMovementBase):
    """Schema de resposta para CaseMovement"""
    id: int
    legal_action_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# ========== Deadline Schemas ==========

class DeadlineBase(BaseModel):
    """Schema base para Deadline"""
    title: str = Field(..., min_length=3)
    description: Optional[str] = None
    deadline_type: Optional[str] = None
    due_date: date
    status: DeadlineStatus = DeadlineStatus.PENDING


class DeadlineCreate(DeadlineBase):
    """Schema para criação de prazo"""
    pass


class DeadlineUpdate(BaseModel):
    """Schema para atualização de prazo"""
    title: Optional[str] = Field(None, min_length=3)
    description: Optional[str] = None
    deadline_type: Optional[str] = None
    due_date: Optional[date] = None
    completion_date: Optional[date] = None
    status: Optional[DeadlineStatus] = None


class DeadlineResponse(DeadlineBase):
    """Schema de resposta para Deadline"""
    id: int
    legal_action_id: int
    completion_date: Optional[date] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# ========== LegalAction Schemas ==========

class LegalActionBase(BaseModel):
    """Schema base para LegalAction"""
    number: str = Field(..., min_length=3)
    title: str = Field(..., min_length=3)
    description: Optional[str] = None
    action_type: LegalActionType
    legal_status: LegalStatus = LegalStatus.PRE_TRIAL
    court_name: Optional[str] = None
    court_segment: Optional[str] = None
    filing_date: Optional[date] = None


class LegalActionCreate(LegalActionBase):
    """Schema para criação de ação jurídica"""
    client_id: int


class LegalActionUpdate(BaseModel):
    """Schema para atualização de ação jurídica"""
    title: Optional[str] = Field(None, min_length=3)
    description: Optional[str] = None
    action_type: Optional[LegalActionType] = None
    legal_status: Optional[LegalStatus] = None
    court_name: Optional[str] = None
    court_segment: Optional[str] = None
    filing_date: Optional[date] = None
    closing_date: Optional[date] = None
    is_active: Optional[bool] = None


class LegalActionResponse(LegalActionBase):
    """Schema de resposta para LegalAction"""
    id: int
    client_id: int
    user_id: int
    closing_date: Optional[date] = None
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class LegalActionDetailResponse(LegalActionResponse):
    """Schema detalhado de LegalAction com partes, movimentações e prazos"""
    parties: list[PartyResponse] = []
    movements: list[CaseMovementResponse] = []
    deadlines: list[DeadlineResponse] = []


class LegalActionListResponse(BaseModel):
    """Schema para lista de ações jurídicas"""
    total: int
    legal_actions: list[LegalActionResponse]
