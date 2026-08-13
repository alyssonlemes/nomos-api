from datetime import date
from typing import Optional, List

from pydantic import BaseModel, ConfigDict


class JurimetriaChatContext(BaseModel):
    tribunal: Optional[str] = None
    classe_processual: Optional[str] = None
    area_juridica_principal: Optional[str] = None
    data_ajuizamento: Optional[date] = None


class JurimetriaChatRequest(BaseModel):
    message: str
    context: Optional[JurimetriaChatContext] = None


class JurimetriaChatPrediction(BaseModel):
    tribunal: str
    classe_processual: Optional[str] = None
    area_juridica_principal: Optional[str] = None
    data_ajuizamento: date
    tempo_total_estimado_dias: int
    tempo_decorrido_dias: Optional[int] = None
    tempo_estimado_restante_dias: Optional[int] = None
    fonte_dados: str = "Manual"

    model_config = ConfigDict(from_attributes=True)


class JurimetriaChatResponse(BaseModel):
    message: str
    prediction: Optional[JurimetriaChatPrediction] = None
    missing_fields: Optional[List[str]] = None
    extracted_fields: Optional[JurimetriaChatContext] = None

    model_config = ConfigDict(from_attributes=True)
