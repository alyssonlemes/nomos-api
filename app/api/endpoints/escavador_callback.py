import hmac
import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.database import get_db
from app.services.escavador_callback_service import EscavadorCallbackService

logger = logging.getLogger(__name__)

router = APIRouter()

def _token_autorizado(header: str | None) -> bool:
    esperado = (settings.ESCAVADOR_CALLBACK_TOKEN or "").strip()
    if not esperado:
        return False
    recebido = (header or "").strip()
    if recebido.lower().startswith("bearer "):
        recebido = recebido[7:].strip()
    if len(recebido) != len(esperado):
        return False
    return hmac.compare_digest(recebido, esperado)

@router.post("/callback", summary="Callback de movimentações do Escavador")
async def receber_callback(request: Request, db: Session = Depends(get_db)):
    """
    O Escavador envia POST com Authorization Bearer do token gerado no painel.
    A URL pública desta rota é cadastrada na página de callbacks do painel.
    """
    if not _token_autorizado(request.headers.get("authorization")):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Callback não autorizado",
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

    event = payload.get("event")
    logger.info("Callback de acompanhamento recebido: event=%s", event if isinstance(event, str) else "invalido")
    EscavadorCallbackService.processar(db, payload)
    return {"ok": True}
