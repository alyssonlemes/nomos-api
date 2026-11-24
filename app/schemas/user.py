from pydantic import BaseModel, EmailStr, Field, ConfigDict, model_validator
from typing import Optional
from datetime import datetime

class UserBase(BaseModel):
    """Schema base para User"""
    email: EmailStr
    full_name: Optional[str] = None

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

class PermissaoModulo(BaseModel):
    """CRUD de um módulo."""
    modulo: str
    visualizar: bool = False
    criar: bool = False
    editar: bool = False
    excluir: bool = False

class UserRoleUpdate(BaseModel):
    """Atribui um perfil de acesso. Aceita profile_id ou o papel legado."""
    profile_id: Optional[int] = Field(None, description="ID do perfil na organização")
    role: Optional[str] = Field(None, description="Papel legado: ADMIN, OWNER, MEMBER, VIEWER, ASSISTANT, GESTOR")

    @model_validator(mode="after")
    def exigir_perfil(self):
        if self.profile_id is None and not (self.role and self.role.strip()):
            raise ValueError("Informe o perfil do usuário")
        return self

class UserLogin(BaseModel):
    """Schema para login"""
    email: EmailStr = Field(..., description="Email do usuário")
    password: str = Field(..., description="Senha do usuário")

class UserResponse(UserBase):
    """Schema de resposta para User"""
    id: int
    role: Optional[str] = None
    profile_id: Optional[int] = None
    profile_name: Optional[str] = None
    isolate_data: bool = False
    permissions: list[PermissaoModulo] = []
    organization_id: Optional[int] = None
    is_active: bool
    is_superuser: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

class UserListResponse(BaseModel):
    """Schema para lista paginada de usuários"""
    total: int
    users: list[UserResponse]
    skip: int = 0
    limit: int = 10

class UserInDB(UserResponse):
    """Schema de User no banco (inclui senha hasheada)"""
    hashed_password: str

class Token(BaseModel):
    """Schema de resposta do token"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # segundos até expirar
    expires_at: datetime  # timestamp de expiração

class TokenData(BaseModel):
    """Schema dos dados contidos no token"""
    email: Optional[str] = None
