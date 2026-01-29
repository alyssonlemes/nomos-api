from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import Optional
from datetime import datetime


# ========== Base Schemas ==========

class UserBase(BaseModel):
    """Schema base para User"""
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)
    full_name: Optional[str] = None


# ========== Request Schemas ==========

class UserCreate(UserBase):
    """Schema para criação de usuário"""
    password: str = Field(..., min_length=6, description="Senha com no mínimo 6 caracteres")
    organization_id: int


class UserUpdate(BaseModel):
    """Schema para atualização de usuário"""
    email: Optional[EmailStr] = None
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    full_name: Optional[str] = None
    password: Optional[str] = Field(None, min_length=6)
    is_active: Optional[bool] = None


class UserLogin(BaseModel):
    """Schema para login"""
    username: str = Field(..., description="Username do usuário")
    password: str = Field(..., description="Senha do usuário")


# ========== Response Schemas ==========

class UserResponse(UserBase):
    """Schema de resposta para User"""
    id: int
    organization_id: int
    is_active: bool
    is_superuser: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class UserInDB(UserResponse):
    """Schema de User no banco (inclui senha hasheada)"""
    hashed_password: str


# ========== Token Schemas ==========

class Token(BaseModel):
    """Schema de resposta do token"""
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Schema dos dados contidos no token"""
    username: Optional[str] = None
