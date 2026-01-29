from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import Optional
from datetime import datetime
from enum import Enum


# ========== Enums ==========

class ClientType(str, Enum):
    """Tipo de cliente"""
    INDIVIDUAL = "individual"
    BUSINESS = "business"


class ClientStatus(str, Enum):
    """Status do cliente"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    PROSPECT = "prospect"
    ARCHIVED = "archived"


# ========== Base Schemas ==========

class ClientBase(BaseModel):
    """Schema base para Client"""
    name: str = Field(..., min_length=3, max_length=200)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=20)
    document: str = Field(..., description="CPF ou CNPJ")
    client_type: ClientType = ClientType.INDIVIDUAL
    status: ClientStatus = ClientStatus.PROSPECT
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = Field(None, max_length=2)
    zip_code: Optional[str] = Field(None, max_length=10)
    notes: Optional[str] = None
    company_name: Optional[str] = Field(None, max_length=200)


# ========== Request Schemas ==========

class ClientCreate(ClientBase):
    """Schema para criação de cliente"""
    pass


class ClientUpdate(BaseModel):
    """Schema para atualização de cliente"""
    name: Optional[str] = Field(None, min_length=3, max_length=200)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=20)
    document: Optional[str] = None
    client_type: Optional[ClientType] = None
    status: Optional[ClientStatus] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = Field(None, max_length=2)
    zip_code: Optional[str] = Field(None, max_length=10)
    notes: Optional[str] = None
    company_name: Optional[str] = Field(None, max_length=200)
    is_active: Optional[bool] = None


# ========== Response Schemas ==========

class ClientResponse(ClientBase):
    """Schema de resposta para Client"""
    id: int
    organization_id: int
    user_id: Optional[int] = None
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class ClientListResponse(BaseModel):
    """Schema para lista de clientes com metadados"""
    total: int
    clients: list[ClientResponse]
