from datetime import date, datetime, timedelta
from typing import List, Optional

from pydantic import BaseModel, Field, ConfigDict


def _default_data_fim() -> date:
    return datetime.now().date()


def _default_data_inicio() -> date:
    return (datetime.now() - timedelta(days=7)).date()


class BatchFiltroRequest(BaseModel):
    """
    Filtros para execução em lote no DataJud
    """
    tribunal_alias: str = Field(..., min_length=2, max_length=50)
    data_inicio: date = Field(default_factory=_default_data_inicio)
    data_fim: date = Field(default_factory=_default_data_fim)
    classe_processual: Optional[str] = None
    assunto_codigo: Optional[str] = None
    size: int = Field(10, ge=1, le=10000)


class ProcessoBatchResult(BaseModel):
    """
    Resultado simplificado por processo
    """
    numero_processo: str
    data_ajuizamento: date

    model_config = ConfigDict(from_attributes=True)


class BatchResponse(BaseModel):
    """
    Resposta da execução batch
    """
    total_processos: int
    processos_processados: int
    resultados: List[ProcessoBatchResult]
