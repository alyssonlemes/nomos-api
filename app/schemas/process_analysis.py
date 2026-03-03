"""
Schemas para Análise de Processos Judiciais.

Estrutura de dados conforme Seção 4 do Master Prompt:
- ProcessoAnalisado: dados individuais por processo (Seção 4.1)
- EstatisticasArea: agregação por área jurídica (Seção 4.2)
- Schemas de request/response para os endpoints de análise
"""

from datetime import date
from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


# ────────────────────────── Dados individuais (Seção 4.1) ──────────────────────

class ClasseProcessualInfo(BaseModel):
    """Informação da classe processual do processo."""
    codigo: Optional[str] = None
    nome: Optional[str] = None


class AssuntoInfo(BaseModel):
    """Informação de um assunto relacionado ao processo."""
    codigo: Optional[str] = None
    nome: Optional[str] = None


class MovimentoInfo(BaseModel):
    """Movimento processual simplificado."""
    nome: str
    data_hora: Optional[str] = None
    codigo: Optional[str] = None


class ProcessoAnalisado(BaseModel):
    """
    Estrutura de dados de processo individual conforme Seção 4.1 do MD.

    Contém todos os campos necessários para consumo pelo modelo de IA,
    seja via fine-tuning ou RAG.
    """
    numero_processo: str
    tribunal: str
    area_juridica_principal: Optional[str] = None
    classe_principal: Optional[ClasseProcessualInfo] = None
    assuntos_relacionados: List[AssuntoInfo] = []
    data_ajuizamento: Optional[date] = None
    data_fim: Optional[date] = None
    duracao_dias: Optional[int] = None
    status_processo: str = "em_andamento"
    movimento_encerramento: Optional[str] = None
    movimentos_principais: List[MovimentoInfo] = []

    model_config = ConfigDict(from_attributes=True)


# ────────────────────────── Estatísticas Agregadas (Seção 4.2) ──────────────────

class EstatisticasArea(BaseModel):
    """
    Estatísticas agregadas por área jurídica conforme Seção 4.2 do MD.

    Inclui tempo médio, desvio padrão e percentis para processos finalizados.
    """
    area: str
    tempo_medio_dias: Optional[float] = None
    desvio_padrao_dias: Optional[float] = None
    total_processos_finalizados: int = 0
    total_processos_em_andamento: int = 0
    percentil_25_dias: Optional[float] = None
    percentil_50_dias: Optional[float] = None
    percentil_75_dias: Optional[float] = None
    percentil_90_dias: Optional[float] = None
    duracao_minima_dias: Optional[int] = None
    duracao_maxima_dias: Optional[int] = None


class EstatisticasTribunal(BaseModel):
    """Estatísticas por tribunal."""
    tribunal: str
    total_processos: int = 0
    total_finalizados: int = 0
    total_em_andamento: int = 0
    tempo_medio_dias: Optional[float] = None
    areas: List[EstatisticasArea] = []


# ────────────────────────── Requests ──────────────────────────────────────────

class AnaliseProcessosFiltro(BaseModel):
    """
    Filtros para análise de processos.

    Permite filtrar por tribunal, área jurídica, classe, assunto e período.
    """
    tribunal_alias: str = Field(
        ...,
        min_length=2,
        max_length=50,
        description="Alias do tribunal (ex: tjsp, tjrj, tjmg)"
    )
    area_juridica: Optional[str] = Field(
        None,
        description="Área jurídica para filtro (Criminal, Família, Cível, Trabalhista, Militar)"
    )
    classe_codigo: Optional[str] = Field(
        None,
        description="Código TPU da classe processual"
    )
    assunto_codigo: Optional[str] = Field(
        None,
        description="Código TPU do assunto"
    )
    data_inicio: Optional[date] = Field(
        None,
        description="Data de ajuizamento mínima"
    )
    data_fim: Optional[date] = Field(
        None,
        description="Data de ajuizamento máxima"
    )
    size: int = Field(
        100,
        ge=1,
        le=10000,
        description="Quantidade máxima de processos por página"
    )
    usar_search_after: bool = Field(
        True,
        description="Usar paginação search_after para coleta massiva (recomendado)"
    )
    max_paginas: int = Field(
        10,
        ge=1,
        le=100,
        description="Número máximo de páginas a buscar"
    )


class AnaliseEstatisticasFiltro(BaseModel):
    """Filtros para consulta de estatísticas agregadas."""
    tribunal: Optional[str] = Field(
        None,
        description="Filtrar por tribunal específico"
    )
    area_juridica: Optional[str] = Field(
        None,
        description="Filtrar por área jurídica específica"
    )


# ────────────────────────── Responses ──────────────────────────────────────────

class AnaliseProcessosResponse(BaseModel):
    """Resposta da coleta e análise de processos."""
    total_processos_encontrados: int
    total_processos_processados: int
    total_finalizados: int
    total_em_andamento: int
    processos: List[ProcessoAnalisado] = []
    estatisticas: Optional[EstatisticasArea] = None


class AnaliseEstatisticasResponse(BaseModel):
    """Resposta da consulta de estatísticas agregadas."""
    total_geral: int
    total_finalizados: int
    total_em_andamento: int
    estatisticas_por_area: List[EstatisticasArea] = []
    estatisticas_por_tribunal: List[EstatisticasTribunal] = []


class AreasDisponiveisResponse(BaseModel):
    """Lista de áreas jurídicas disponíveis no mapeamento TPU."""
    areas: List[Dict[str, object]]
