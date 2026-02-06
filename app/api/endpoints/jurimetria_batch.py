from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user
from app.database import get_db
from app.schemas.jurimetria_batch import BatchFiltroRequest, BatchResponse
from app.services.datajud_batch_service import DataJudBatchService

router = APIRouter()


@router.post(
    "/batch/tempo-tramitacao",
    response_model=BatchResponse,
    status_code=status.HTTP_200_OK,
    summary="Executar jurimetria em lote"
)
def executar_batch_tempo_tramitacao(
    filtros: BatchFiltroRequest,
    db: Session = Depends(get_db),
    _current_user = Depends(get_current_active_user)
):
    """
    Executa a coleta em lote do DataJud para cálculo de tempo de tramitação
    """
    try:
        return DataJudBatchService.run_batch(db=db, filtros=filtros)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno ao processar jurimetria em lote"
        ) from exc
