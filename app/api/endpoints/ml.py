import logging

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import require_legal_actions_access

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/train",
    status_code=status.HTTP_200_OK,
    summary="Treinar modelo de jurimetria"
)
def train_model(
    _current_user = Depends(require_legal_actions_access)
):
    """
    Executa o pipeline completo de treino e registra o modelo ativo.
    """
    # Lazy import to avoid loading sklearn at startup
    from app.ml.train import train_pipeline, MIN_TRAINING_RECORDS
    
    try:
        version, metrics, total_records = train_pipeline()
        return {
            "version": version,
            "metrics": metrics,
            "total_records": total_records
        }
    except ValueError as exc:
        logger.warning("Treino abortado por erro de validacao: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Registros insuficientes para treino. Mínimo: {MIN_TRAINING_RECORDS}"
        ) from exc
    except Exception as exc:
        logger.exception("Erro inesperado ao treinar modelo")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno ao treinar modelo"
        ) from exc
