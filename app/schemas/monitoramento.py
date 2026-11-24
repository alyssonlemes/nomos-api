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

class MonitoramentoResponse(BaseModel):
    ativo: bool
    status: Optional[str] = None
    frequencia: Optional[str] = None
    limite: int
    em_uso: int
    prazos: list[ProcessoPrazoResponse] = []
