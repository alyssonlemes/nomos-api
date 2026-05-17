from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime


class OrganizationBase(BaseModel):
    """Schema base para Organization"""
    name: str = Field(..., min_length=3, max_length=200)
    document: Optional[str] = Field(None, max_length=20)
    legal_representative_name: Optional[str] = Field(None, max_length=200)
    legal_representative_document: Optional[str] = Field(None, max_length=20)


class OrganizationCreate(OrganizationBase):
    """Schema para criação de organização"""
    pass


class OrganizationUpdate(BaseModel):
    """Schema para atualização de organização"""
    name: Optional[str] = Field(None, min_length=3, max_length=200)
    document: Optional[str] = Field(None, max_length=20)
    legal_representative_name: Optional[str] = Field(None, max_length=200)
    legal_representative_document: Optional[str] = Field(None, max_length=20)
    is_active: Optional[bool] = None


class OrganizationResponse(OrganizationBase):
    """Schema de resposta para Organization"""
    id: int
    owner_id: int
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
