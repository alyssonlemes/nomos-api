from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import require_legal_actions_access
from app.database import get_db
from app.schemas.jurimetria_batch import BatchFiltroRequest, BatchResponse
from app.services.datajud_batch_service import DataJudBatchService


router = APIRouter()


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

