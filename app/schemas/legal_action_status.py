from pydantic import BaseModel, Field, ConfigDict
from typing import Optional


class LegalActionStatusBase(BaseModel):
    """Schema base para status jurídico de ação."""

    name: str = Field(..., min_length=1, max_length=100, description="Nome do status")
    code: str = Field(..., min_length=1, max_length=50, description="Código único (ex: pre_trial)")
    description: Optional[str] = None


class LegalActionStatusCreate(LegalActionStatusBase):
    """Schema para criação de status jurídico de ação."""

    pass


class LegalActionStatusUpdate(BaseModel):
    """Schema para atualização de status jurídico de ação."""

    name: Optional[str] = Field(None, min_length=1, max_length=100)
    code: Optional[str] = Field(None, min_length=1, max_length=50)
    description: Optional[str] = None


class LegalActionStatusResponse(LegalActionStatusBase):
    """Schema de resposta para status jurídico de ação."""

    id: int

    model_config = ConfigDict(from_attributes=True)


class LegalActionStatusListResponse(BaseModel):
    """Schema de listagem de status jurídicos de ação."""

    total: int
    legal_action_statuses: list[LegalActionStatusResponse]

