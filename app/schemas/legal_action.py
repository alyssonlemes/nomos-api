from pydantic import BaseModel, Field, ConfigDict
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


# ========== LegalAction Schemas ==========

class LegalActionBase(BaseModel):
    """Schema base para LegalAction"""
    number: str = Field(..., min_length=3, description="Número único do processo")
    title: str = Field(..., min_length=3, description="Título da ação")
    description: Optional[str] = None
    action_type: LegalActionType
    legal_status: LegalStatus = LegalStatus.PRE_TRIAL
    court_name: Optional[str] = None
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
    filing_date: Optional[date] = None
    closing_date: Optional[date] = None


class LegalActionResponse(LegalActionBase):
    """Schema de resposta para LegalAction"""
    id: int
    client_id: int
    organization_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class LegalActionResponse(LegalActionBase):
    """Schema de resposta para LegalAction"""
    id: int
    client_id: int
    organization_id: int
    user_id: Optional[int] = None
    closing_date: Optional[date] = None
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class LegalActionListResponse(BaseModel):
    """Schema para lista de ações jurídicas"""
    total: int
    legal_actions: list[LegalActionResponse]
