import hmac
import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.database import get_db
from app.services.jurimai_callback_service import JurimaiCallbackService
from app.services.jurimai_client import JurimaiError

logger = logging.getLogger(__name__)

router = APIRouter()


def _token_autorizado(recebido: str | None) -> bool:
    esperado = (settings.JURIMAI_CALLBACK_TOKEN or "").strip()
    if not esperado:
        return False
    valor = (recebido or "").strip()
    if valor.lower().startswith("bearer "):
        valor = valor[7:].strip()
    if len(valor) != len(esperado):
        return False
    return hmac.compare_digest(valor, esperado)


@router.post("/callback", summary="Aviso de novidade da Juri+")
async def receber_callback(
    request: Request,
    token: str | None = Query(None),
    db: Session = Depends(get_db),
):
    """
    A URL desta rota, com o token na query, é enviada à Juri+ ao ligar o acompanhamento.
    """
    if not _token_autorizado(token or request.headers.get("authorization")):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Aviso não autorizado",
        )

    try:
        payload = await request.json()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="JSON inválido",
        ) from exc

    if not isinstance(payload, dict):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="JSON inválido",
        )

    logger.info("Aviso de acompanhamento recebido")
    try:
        JurimaiCallbackService.processar(db, payload)
    except JurimaiError as exc:
        raise HTTPException(status_code=exc.status_code if exc.status_code < 500 else 502, detail=str(exc)) from exc
    return {"ok": True}
