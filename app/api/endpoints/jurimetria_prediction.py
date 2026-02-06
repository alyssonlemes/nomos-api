from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_current_active_user
from app.schemas.jurimetria_prediction import JurimetriaPredictionResponse
from app.services.jurimetria_prediction_service import JurimetriaPredictionService

router = APIRouter()


@router.post(
    "/previsao-tempo/{tribunal}/{numero_processo}",
    response_model=JurimetriaPredictionResponse,
    status_code=status.HTTP_200_OK,
    summary="Prever tempo de tramitação de processo"
)
def prever_tempo_tramitacao(
    tribunal: str,
    numero_processo: str,
    _current_user = Depends(get_current_active_user)
):
    """
    Consulta DataJud e retorna previsão de tempo de tramitação.
    """
    try:
        return JurimetriaPredictionService.predict(tribunal=tribunal, numero_processo=numero_processo)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except RuntimeError as exc:
        message = str(exc)
        if "Modelo ativo" in message:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=message) from exc
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=message) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno ao processar predição"
        ) from exc
