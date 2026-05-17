from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import require_legal_actions_access
from app.schemas.jurimetria_prediction import JurimetriaPredictionResponse
from app.schemas.jurimetria_chat import (
    JurimetriaChatRequest,
    JurimetriaChatResponse,
    JurimetriaChatPrediction,
    JurimetriaChatContext,
)

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
    _current_user = Depends(require_legal_actions_access)
):
    """
    Consulta DataJud e retorna previsão de tempo de tramitação.
    """
    # Lazy import to avoid loading sklearn at startup
    from app.services.jurimetria_prediction_service import JurimetriaPredictionService
    
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


@router.post(
    "/chat",
    response_model=JurimetriaChatResponse,
    status_code=status.HTTP_200_OK,
    summary="Assistente de jurimetria por linguagem natural",
)
def jurimetria_chat(
    payload: JurimetriaChatRequest,
    _current_user = Depends(require_legal_actions_access),
):
    """
    Recebe uma mensagem em linguagem natural, extrai features e gera a previsão.
    """
    from app.services.jurimetria_prediction_service import JurimetriaPredictionService

    try:
        context = payload.context.model_dump() if payload.context else None
        extracted, missing = JurimetriaPredictionService.parse_chat_message(
            payload.message,
            context=context,
        )

        extracted_context = JurimetriaChatContext(**extracted)

        if missing:
            missing_list = ", ".join(missing)
            message = (
                "Preciso de mais informacoes para estimar o tempo. "
                f"Informe: {missing_list}. "
                "Exemplo: tribunal=tjsp e data_ajuizamento=2023-01-10."
            )
            return JurimetriaChatResponse(
                message=message,
                missing_fields=missing,
                extracted_fields=extracted_context,
            )

        prediction = JurimetriaPredictionService.predict_from_features(
            tribunal=extracted.get("tribunal"),
            classe_processual=extracted.get("classe_processual"),
            area_juridica_principal=extracted.get("area_juridica_principal"),
            data_ajuizamento=extracted.get("data_ajuizamento"),
        )

        response_message = (
            "Estimativa gerada. "
            f"Tempo total previsto: {prediction['tempo_total_estimado_dias']} dias."
        )

        return JurimetriaChatResponse(
            message=response_message,
            prediction=JurimetriaChatPrediction(**prediction),
            extracted_fields=extracted_context,
        )
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
            detail="Erro interno ao processar jurimetria"
        ) from exc
