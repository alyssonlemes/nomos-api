from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime, date

from app.schemas.legal_action_type import LegalActionTypeResponse
from app.schemas.legal_action_status import LegalActionStatusResponse


# ========== LegalAction Schemas ==========

class LegalActionBase(BaseModel):
    """Schema base para LegalAction"""
    number: str = Field(..., min_length=3, description="Número único do processo")
    title: str = Field(..., min_length=3, description="Título da ação")
    description: Optional[str] = None
    action_type_id: int = Field(..., description="ID do tipo de ação (catálogo legal_action_types)")
    legal_status_id: Optional[int] = Field(
        None,
        description="ID do status jurídico (catálogo legal_action_statuses). Se vazio, usa 'pre_trial'.",
    )
    court_name: Optional[str] = None
    filing_date: Optional[date] = None


class LegalActionCreate(LegalActionBase):
    """Schema para criação de ação jurídica"""
    client_id: int


class LegalActionUpdate(BaseModel):
    """Schema para atualização de ação jurídica"""
    title: Optional[str] = Field(None, min_length=3)
    description: Optional[str] = None
    action_type_id: Optional[int] = None
    # Accept either an explicit `legal_status_id` or a `legal_status` code (ex: "litigation")
    legal_status_id: Optional[int] = None
    legal_status: Optional[str] = None
    court_name: Optional[str] = None
    filing_date: Optional[date] = None
    closing_date: Optional[date] = None


class LegalActionResponse(BaseModel):
    """Schema de resposta para LegalAction (com tipo aninhado)"""
    id: int
    number: str
    title: str
    description: Optional[str] = None
    action_type_id: int
    action_type: Optional[LegalActionTypeResponse] = None
    legal_status_id: int
    legal_status: Optional[LegalActionStatusResponse] = None
    court_name: Optional[str] = None
    filing_date: Optional[date] = None
    closing_date: Optional[date] = None
    client_id: int
    organization_id: int
    user_id: Optional[int] = None
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class LegalActionListResponse(BaseModel):
    """Schema para lista de ações jurídicas"""
    total: int
    legal_actions: list[LegalActionResponse]
