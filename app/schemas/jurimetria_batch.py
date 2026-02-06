from datetime import date
from typing import List, Optional

from pydantic import BaseModel, Field, ConfigDict


class BatchFiltroRequest(BaseModel):
    """
    Filtros para execução em lote no DataJud
    """
    tribunal_alias: str = Field(..., min_length=2, max_length=50)
    data_inicio: date
    data_fim: date
    classe_processual: Optional[str] = None
    assunto_codigo: Optional[str] = None
    size: int = Field(100, ge=1, le=1000)


class ProcessoBatchResult(BaseModel):
    """
    Resultado simplificado por processo
    """
    numero_processo: str
    data_ajuizamento: date
    data_ultima_movimentacao: Optional[date] = None
    tempo_tramitacao_dias: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class BatchResponse(BaseModel):
    """
    Resposta da execução batch
    """
    total_processos: int
    processos_processados: int
    resultados: List[ProcessoBatchResult]
