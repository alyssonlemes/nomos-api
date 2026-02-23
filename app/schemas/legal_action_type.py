from pydantic import BaseModel, Field, ConfigDict
from typing import Optional


class LegalActionTypeBase(BaseModel):
    """Schema base para tipo de ação jurídica"""
    name: str = Field(..., min_length=1, max_length=100, description="Nome do tipo")
    code: str = Field(..., min_length=1, max_length=50, description="Código único (ex: labor, civil)")
    description: Optional[str] = None


class LegalActionTypeCreate(LegalActionTypeBase):
    """Schema para criação de tipo de ação jurídica"""
    pass


class LegalActionTypeUpdate(BaseModel):
    """Schema para atualização de tipo de ação jurídica"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    code: Optional[str] = Field(None, min_length=1, max_length=50)
    description: Optional[str] = None


class LegalActionTypeResponse(LegalActionTypeBase):
    """Schema de resposta para tipo de ação jurídica"""
    id: int

    model_config = ConfigDict(from_attributes=True)


class LegalActionTypeListResponse(BaseModel):
    """Schema para listagem de tipos de ação jurídica"""
    total: int
    legal_action_types: list[LegalActionTypeResponse]
