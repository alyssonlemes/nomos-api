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
    user_ids: Optional[list[int]] = Field(
        None,
        description="IDs de usuários vinculados ao processo (mesma organização).",
    )
    court_name: Optional[str] = None
    filing_date: Optional[date] = None
    tribunal: Optional[str] = None
    comarca: Optional[str] = None
    vara: Optional[str] = None
    orgao_julgador: Optional[str] = None
    competencia: Optional[str] = None
    magistrado: Optional[str] = None
    classe_processual_codigo: Optional[str] = None
    classe_processual_nome: Optional[str] = None
    assuntos_json: Optional[str] = None
    data_distribuicao: Optional[date] = None
    valor_causa: Optional[float] = None
    segredo_justica: Optional[bool] = False


class ProcessoParteCreate(BaseModel):
    polo: Optional[str] = None
    tipo_participacao: Optional[str] = None
    nome: str
    documento: Optional[str] = None
    oab: Optional[str] = None
    client_id: Optional[int] = None

class ProcessoMovimentoCreate(BaseModel):
    codigo: Optional[str] = None
    nome: str
    data_hora: Optional[datetime] = None
    complemento_json: Optional[str] = None

class LegalActionCreate(LegalActionBase):
    """Schema para criação de ação jurídica"""
    client_id: int
    partes: Optional[list[ProcessoParteCreate]] = None
    movimentos: Optional[list[ProcessoMovimentoCreate]] = None


class LegalActionUpdate(BaseModel):
    """Schema para atualização de ação jurídica"""
    title: Optional[str] = Field(None, min_length=3)
    description: Optional[str] = None
    action_type_id: Optional[int] = None
    # Accept either an explicit `legal_status_id` or a `legal_status` code (ex: "litigation")
    legal_status_id: Optional[int] = None
    legal_status: Optional[str] = None
    user_ids: Optional[list[int]] = None
    court_name: Optional[str] = None
    filing_date: Optional[date] = None
    closing_date: Optional[date] = None
    client_id: Optional[int] = None
    partes: Optional[list[ProcessoParteCreate]] = None
    movimentos: Optional[list[ProcessoMovimentoCreate]] = None

    # Campos DataJud opcionais
    tribunal: Optional[str] = None
    comarca: Optional[str] = None
    vara: Optional[str] = None
    orgao_julgador: Optional[str] = None
    competencia: Optional[str] = None
    magistrado: Optional[str] = None
    classe_processual_codigo: Optional[str] = None
    classe_processual_nome: Optional[str] = None
    assuntos_json: Optional[str] = None
    data_distribuicao: Optional[date] = None
    valor_causa: Optional[float] = None
    segredo_justica: Optional[bool] = None


class LegalActionAssignedUserResponse(BaseModel):
    id: int
    full_name: Optional[str] = None
    email: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ProcessoParteResponse(BaseModel):
    id: int
    polo: Optional[str] = None
    tipo_participacao: Optional[str] = None
    nome: str
    documento: Optional[str] = None
    oab: Optional[str] = None
    client_id: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class ProcessoMovimentoResponse(BaseModel):
    id: int
    codigo: Optional[str] = None
    nome: str
    data_hora: Optional[datetime] = None
    complemento_json: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


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
    assigned_users: list[LegalActionAssignedUserResponse] = []
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    # Campos DataJud
    tribunal: Optional[str] = None
    comarca: Optional[str] = None
    vara: Optional[str] = None
    orgao_julgador: Optional[str] = None
    competencia: Optional[str] = None
    magistrado: Optional[str] = None
    classe_processual_codigo: Optional[str] = None
    classe_processual_nome: Optional[str] = None
    assuntos_json: Optional[str] = None
    data_distribuicao: Optional[date] = None
    valor_causa: Optional[float] = None
    segredo_justica: Optional[bool] = False
    datajud_synced_at: Optional[datetime] = None

    partes: list[ProcessoParteResponse] = []
    movimentos: list[ProcessoMovimentoResponse] = []

    model_config = ConfigDict(from_attributes=True)


class LegalActionListResponse(BaseModel):
    """Schema para lista de ações jurídicas"""
    total: int
    legal_actions: list[LegalActionResponse]
