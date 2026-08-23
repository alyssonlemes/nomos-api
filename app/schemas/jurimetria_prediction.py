from typing import Optional

from pydantic import BaseModel, ConfigDict


class JurimetriaPredictionResponse(BaseModel):
    """
    Resposta da predição de tempo de tramitação
    """
    numero_processo: str
    tribunal: str
    tempo_total_estimado_dias: int
    tempo_decorrido_dias: Optional[int] = None
    tempo_estimado_restante_dias: Optional[int] = None
    status: str = "em_andamento"
    fonte_dados: str = "DataJud"

    model_config = ConfigDict(from_attributes=True)
