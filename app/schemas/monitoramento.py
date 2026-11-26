from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict

class ProcessoPrazoResponse(BaseModel):
    id: int
    origem: str
    conteudo: str
    data_movimentacao: Optional[date] = None
    dias_prazo: Optional[int] = None
    data_vencimento: Optional[date] = None
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class PublicacaoItem(BaseModel):
    id: int
    legal_action_id: int
    numero: str
    titulo: str
    conteudo: str
    data_movimentacao: Optional[datetime] = None
    tratado_em: Optional[datetime] = None
    prazo_status: Optional[str] = None
    prazo_vencimento: Optional[date] = None
    dias_prazo: Optional[int] = None


class PublicacaoListResponse(BaseModel):
    total: int
    pendentes: int
    publicacoes: list[PublicacaoItem]


class MonitoramentoResponse(BaseModel):
    ativo: bool
    status: Optional[str] = None
    frequencia: Optional[str] = None
    limite: int
    em_uso: int
    prazos: list[ProcessoPrazoResponse] = []
