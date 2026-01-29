from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime


# ========== Base Schemas ==========

class OrganizationBase(BaseModel):
    """Schema base para Organization"""
    name: str = Field(..., min_length=3, max_length=200, description="Nome da organização/escritório")
    document: Optional[str] = Field(None, max_length=20, description="CNPJ da organização")


# ========== Request Schemas ==========

class OrganizationCreate(OrganizationBase):
    """Schema para criação de organização"""
    pass


class OrganizationUpdate(BaseModel):
    """Schema para atualização de organização"""
    name: Optional[str] = Field(None, min_length=3, max_length=200)
    document: Optional[str] = Field(None, max_length=20)
    is_active: Optional[bool] = None


# ========== Response Schemas ==========

class OrganizationResponse(OrganizationBase):
    """Schema de resposta para Organization"""
    id: int
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class OrganizationWithStats(OrganizationResponse):
    """Schema de resposta com estatísticas"""
    total_users: int = 0
    total_clients: int = 0
    total_legal_actions: int = 0

    model_config = ConfigDict(from_attributes=True)
