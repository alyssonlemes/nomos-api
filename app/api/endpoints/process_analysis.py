"""
Endpoints de Análise de Processos Judiciais.

Implementa os endpoints RESTful para:
- Coleta e análise de processos via DataJud (com search_after e análise de movimentos)
- Consulta de estatísticas agregadas (tempo médio, percentis por área)
- Listagem de áreas jurídicas disponíveis (mapeamento TPU)
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import require_legal_actions_access
from app.database import get_db
from app.schemas.process_analysis import (
    AnaliseEstatisticasFiltro,
    AnaliseEstatisticasResponse,
    AnaliseProcessosFiltro,
    AnaliseProcessosResponse,
    AreasDisponiveisResponse,
)
from app.services.process_analysis_service import ProcessAnalysisService
from app.services.tpu_mapping import listar_areas_disponiveis

router = APIRouter()


@router.post(
    "/coletar-analisar",
    response_model=AnaliseProcessosResponse,
    status_code=status.HTTP_200_OK,
    summary="Coletar e analisar processos do DataJud",
)
def coletar_e_analisar_processos(
    filtros: AnaliseProcessosFiltro,
    db: Session = Depends(get_db),
    _current_user=Depends(require_legal_actions_access),
):
    """
    Coleta processos da API pública do DataJud e realiza análise completa.

    **Funcionalidades:**
    - Filtragem por área jurídica (Criminal, Família, Cível, Trabalhista, Militar, etc.)
    - Filtragem por classe processual ou assunto (códigos TPU)
    - Filtragem por período de ajuizamento
    - Paginação via `search_after` para coleta massiva (sem limite de 10k)
    - Inferência de data de encerramento a partir dos movimentos processuais
    - Cálculo de duração em dias para processos finalizados
    - Classificação automática de área jurídica via mapeamento TPU
    - Estatísticas agregadas (tempo médio, desvio padrão, percentis)

    **Exemplo de uso:**
    ```json
    {
        "tribunal_alias": "tjsp",
        "area_juridica": "Criminal",
        "data_inicio": "2023-01-01",
        "data_fim": "2023-12-31",
        "size": 100,
        "usar_search_after": true,
        "max_paginas": 5
    }
    ```
    """
    try:
        return ProcessAnalysisService.coletar_e_analisar(db=db, filtros=filtros)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)
        ) from exc
    except Exception as exc:  # pragma: no cover
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno ao processar análise de processos",
        ) from exc


@router.post(
    "/estatisticas",
    response_model=AnaliseEstatisticasResponse,
    status_code=status.HTTP_200_OK,
    summary="Obter estatísticas agregadas de processos",
)
def obter_estatisticas_processos(
    filtros: AnaliseEstatisticasFiltro,
    db: Session = Depends(get_db),
    _current_user=Depends(require_legal_actions_access),
):
    """
    Retorna estatísticas agregadas dos processos já coletados e analisados.

    **Dados retornados:**
    - Tempo médio de tramitação por área jurídica
    - Desvio padrão
    - Percentis (P25, P50/mediana, P75, P90)
    - Duração mínima e máxima
    - Total de processos finalizados e em andamento
    - Breakdown por tribunal

    **Exemplo de uso:**
    ```json
    {
        "tribunal": "tjsp",
        "area_juridica": "Criminal"
    }
    ```

    Para obter estatísticas de todas as áreas, envie um body vazio `{}`.
    """
    try:
        return ProcessAnalysisService.obter_estatisticas(db=db, filtros=filtros)
    except Exception as exc:  # pragma: no cover
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno ao calcular estatísticas",
        ) from exc


@router.get(
    "/areas-juridicas",
    response_model=AreasDisponiveisResponse,
    status_code=status.HTTP_200_OK,
    summary="Listar áreas jurídicas disponíveis",
)
def listar_areas_juridicas(
    _current_user=Depends(require_legal_actions_access),
):
    """
    Retorna todas as áreas jurídicas disponíveis no mapeamento TPU.

    Cada área inclui:
    - Nome da área (ex: Criminal, Família, Cível)
    - Total de códigos de classes processuais mapeados
    - Total de códigos de assuntos mapeados
    - Lista dos códigos TPU correspondentes

    Útil para saber quais áreas podem ser usadas como filtro na coleta.
    """
    return AreasDisponiveisResponse(areas=listar_areas_disponiveis())
