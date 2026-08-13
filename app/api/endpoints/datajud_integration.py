from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import require_legal_actions_access, get_user_organization
from app.database import get_db
from app.models.user import User
from app.schemas.datajud_autocomplete import ProcessoAutoCompleteResponse
from app.schemas.jurimetria_batch import BatchFiltroRequest, BatchResponse
from app.services.datajud_autocomplete_service import DataJudAutoCompleteService
from app.services.datajud_batch_service import DataJudBatchService


router = APIRouter()



# ─────────────────── Auto-Complete de Processos ────────────────────────────


@router.get(
    "/autocomplete",
    response_model=ProcessoAutoCompleteResponse,
    status_code=status.HTTP_200_OK,
    summary="Auto-complete de processo via DataJud",
)
def autocomplete_processo(
    numero_cnj: str = Query(
        ...,
        min_length=20,
        description="Número CNJ do processo (ex: 0000001-00.2024.8.26.0001)",
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_legal_actions_access),
):
    """
    Consulta um processo judicial no DataJud pelo número CNJ e retorna os dados
    pré-preenchidos para o formulário de criação/edição de processo.

    **Fluxo:**
    1. Identifica automaticamente o tribunal pelo número CNJ (NUPRO)
    2. Consulta o DataJud via ElasticSearch DSL (term no `numeroProcesso.keyword`)
    3. Mapeia todos os campos relevantes (partes, movimentos, assuntos, tribunal, etc.)
    4. Verifica se o processo já existe na organização
    5. Resolve partes → busca cliente por CPF/CNPJ (exato) ou nome (fuzzy)
    6. Retorna dados prontos para pre-fill + lista de partes não cadastradas

    **Partes não encontradas:** o frontend deve exibir modal de confirmação antes de cadastrar.

    **Erros tratados:**
    - Processo não encontrado → `processo_encontrado=false`
    - Segredo de justiça → `processo_encontrado=true`, `aviso` preenchido
    - Número CNJ inválido → HTTP 422
    - API Key inválida → HTTP 502
    - Rate limit → HTTP 429
    - Timeout → HTTP 504
    - Tribunal não suportado → HTTP 422
    """
    if not current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Você precisa ter uma organização para consultar processos no DataJud.",
        )

    try:
        return DataJudAutoCompleteService.buscar_por_numero(
            numero_cnj=numero_cnj,
            organization_id=current_user.organization_id,
            db=db,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except RuntimeError as exc:
        msg = str(exc)
        if "Rate limit" in msg or "429" in msg:
            raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=msg) from exc
        if "Autenticação" in msg or "401" in msg or "403" in msg:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=msg) from exc
        if "timeout" in msg.lower() or "timed out" in msg.lower():
            raise HTTPException(status_code=status.HTTP_504_GATEWAY_TIMEOUT, detail=msg) from exc
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=msg) from exc
    except Exception as exc:  # pragma: no cover - defensive
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno ao consultar DataJud",
        ) from exc


# ─────────────────── Coleta em Lote (existente) ────────────────────────────


@router.post(
    "/batch/processos",
    response_model=BatchResponse,
    status_code=status.HTTP_200_OK,
    summary="Executar coleta em lote do DataJud",
)
def executar_batch_processos(
    filtros: BatchFiltroRequest,
    db: Session = Depends(get_db),
    _current_user = Depends(require_legal_actions_access),
    organization_id: int = Depends(get_user_organization),
):
    """
    Step 1 - DataJud integration.

    Runs batch collection from DataJud to compute derived fields
    (for example, time to disposition) and persists normalized data
    for later data preparation and model training steps.
    """
    try:
        return DataJudBatchService.run_batch(db=db, filtros=filtros)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - defensive
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno ao processar coleta em lote do DataJud",
        ) from exc


