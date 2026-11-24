"""Cliente da API de monitoramento de processos do Escavador (v2).

Contrato lido em https://api.escavador.com/v2/docs/monitoramento-de-processos
"""

from __future__ import annotations

import json
import logging
from typing import Any
from urllib import error, request

from app.core.config import settings

logger = logging.getLogger(__name__)

FREQUENCIA_DIARIA = "DIARIA"

class EscavadorError(Exception):
    def __init__(self, message: str, status_code: int, body: dict[str, Any] | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.body = body or {}

class EscavadorClient:
    def __init__(self, token: str | None = None, base_url: str | None = None):
        self._token = token if token is not None else settings.ESCAVADOR_API_TOKEN
        self._base = (base_url or settings.ESCAVADOR_API_BASE).rstrip("/")

    def criar_monitoramento(self, numero: str) -> dict[str, Any]:
        """POST /api/v2/monitoramentos/processos. Tribunal fica a cargo do CNJ."""
        return self._enviar(
            "POST",
            "/monitoramentos/processos",
            {
                "numero": numero,
                "frequencia": FREQUENCIA_DIARIA,
                "documentos_publicos": False,
            },
        )

    def remover_monitoramento(self, monitoramento_id: int) -> None:
        """DELETE /api/v2/monitoramentos/processos/{id}."""
        self._enviar("DELETE", f"/monitoramentos/processos/{monitoramento_id}")

    def _enviar(self, method: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        if not self._token:
            raise EscavadorError("ESCAVADOR_API_TOKEN não configurado.", 503)

        data = None
        headers = {
            "Authorization": f"Bearer {self._token}",
            "Accept": "application/json",
        }
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"

        req = request.Request(f"{self._base}{path}", data=data, headers=headers, method=method)
        try:
            with request.urlopen(req, timeout=30) as response:
                raw = response.read().decode("utf-8")
                if not raw or raw.strip() in ("", "[]"):
                    return {}
                parsed = json.loads(raw)
                return parsed if isinstance(parsed, dict) else {}
        except error.HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="replace")
            body = _json_ou_vazio(raw)
            logger.warning("Escavador respondeu %s em %s %s", exc.code, method, path)
            raise EscavadorError(_mensagem_http(exc.code, body), exc.code, body) from exc
        except error.URLError as exc:
            logger.warning("Falha de rede ao chamar Escavador: %s", exc.reason)
            raise EscavadorError("Não foi possível falar com o serviço de acompanhamento.", 504) from exc

def monitoramento_de_conflito(erro: EscavadorError) -> dict[str, Any] | None:
    """422 'Você já monitora este processo' devolve o monitoramento em appends."""
    if erro.status_code != 422:
        return None
    appends = erro.body.get("appends")
    if not isinstance(appends, dict):
        return None
    monitoramento = appends.get("monitoramento")
    if isinstance(monitoramento, dict) and monitoramento.get("id"):
        return monitoramento
    return None

def _json_ou_vazio(raw: str) -> dict[str, Any]:
    try:
        parsed = json.loads(raw) if raw else {}
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}

def _mensagem_http(status_code: int, body: dict[str, Any]) -> str:
    if status_code == 401:
        return "Token do Escavador inválido."
    if status_code == 402:
        return "A conta do Escavador está sem créditos."
    if status_code == 503:
        return "O acompanhamento está em processamento. Tente novamente em alguns segundos."
    mensagem = body.get("message") or body.get("error")
    if isinstance(mensagem, str) and mensagem.strip():
        return mensagem
    return "O serviço de acompanhamento recusou o pedido."
