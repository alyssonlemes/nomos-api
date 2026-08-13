from pydantic import BaseModel, EmailStr, Field, ConfigDict, field_validator
from typing import Optional
from datetime import datetime


# ========== Base Schemas ==========

class UserBase(BaseModel):
    """Schema base para User"""
    email: EmailStr
    full_name: Optional[str] = None


# ========== Request Schemas ==========

class UserCreate(UserBase):
    """Schema para criação de usuário (sem organização obrigatória)"""
    password: str = Field(..., min_length=6, description="Senha com no mínimo 6 caracteres")
    organization_id: Optional[int] = None


class UserRegisterWithOrg(UserBase):
    """Schema para registro de usuário com criação de organização"""
    password: str = Field(..., min_length=6, description="Senha com no mínimo 6 caracteres")
    organization_name: str = Field(..., min_length=3, max_length=200, description="Nome da organização/escritório")
    organization_document: Optional[str] = Field(None, max_length=20, description="CNPJ da organização")


class UserUpdate(BaseModel):
    """Schema para atualização de usuário"""
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    password: Optional[str] = Field(None, min_length=6)
    is_active: Optional[bool] = None


class UserRoleUpdate(BaseModel):
    """Schema para atualização de role do usuário (apenas admin/owner)"""
    role: str = Field(..., description="Papel do usuário: ADMIN, OWNER, MEMBER, VIEWER, ASSISTANT")

    @field_validator('role')
    @classmethod
    def validate_role(cls, v: str) -> str:
        allowed_roles = ['ADMIN', 'OWNER', 'MEMBER', 'VIEWER', 'ASSISTANT']
        role_upper = v.upper()
        if role_upper not in allowed_roles:
            raise ValueError(f'Role deve ser um dos seguintes: {", ".join(allowed_roles)}')
        return role_upper


class UserLogin(BaseModel):
    """Schema para login"""
    email: EmailStr = Field(..., description="Email do usuário")
    password: str = Field(..., description="Senha do usuário")


# ========== Response Schemas ==========

class UserResponse(UserBase):
    """Schema de resposta para User"""
    id: int
    role: Optional[str] = None
    organization_id: Optional[int] = None
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
    expires_in: int  # segundos até expirar
    expires_at: datetime  # timestamp de expiração


class TokenData(BaseModel):
    """Schema dos dados contidos no token"""
    email: Optional[str] = None
