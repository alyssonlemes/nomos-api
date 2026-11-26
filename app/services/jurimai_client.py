"""Cliente da API de monitoramento da Juri+.

Contrato lido em https://jurimais.com.br/docs
O acompanhamento diário custa por processo ativo. Encerrar não cobra.
A lista de movimentações é outra chamada e só entra quando chega um aviso.
"""

from __future__ import annotations

import json
import logging
from typing import Any
from urllib import error, parse, request

from app.core.config import settings
from app.domain.prazo_processual import apenas_digitos

logger = logging.getLogger(__name__)

FREQUENCIA_DIARIA = "diaria"


class JurimaiError(Exception):
    def __init__(self, message: str, status_code: int, body: dict[str, Any] | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.body = body or {}


class JurimaiClient:
    def __init__(self, token: str | None = None, base_url: str | None = None):
        self._token = token if token is not None else settings.JURIMAI_API_TOKEN
        self._base = (base_url or settings.JURIMAI_API_BASE).rstrip("/")

    def criar_monitoramento(self, numero: str, callback_url: str) -> dict[str, Any]:
        """POST /api/v2/monitoramentos. Cobrança mensal do processo acompanhado."""
        return self._enviar(
            "POST",
            "/v2/monitoramentos",
            {
                "tipo": "processo",
                "alvo": numero,
                "frequencia": FREQUENCIA_DIARIA,
                "callback_url": callback_url,
            },
        )

    def listar_monitoramentos(self) -> list[dict[str, Any]]:
        corpo = self._enviar("GET", "/v2/monitoramentos")
        itens = corpo.get("monitoramentos")
        if isinstance(itens, list):
            return [item for item in itens if isinstance(item, dict)]
        return []

    def remover_monitoramento(self, monitoramento_id: int) -> None:
        """DELETE /api/v2/monitoramentos/{id}. A documentação marca esta rota como grátis."""
        self._enviar("DELETE", f"/v2/monitoramentos/{monitoramento_id}")

    def listar_movimentacoes(self, numero: str) -> list[dict[str, Any]]:
        """GET /api/v1/processos/{cnj}/movimentacoes. Cobra quando a resposta é 2xx."""
        digitos = apenas_digitos(numero)
        corpo = self._enviar("GET", f"/v1/processos/{digitos}/movimentacoes")
        itens = corpo.get("movimentacoes")
        if isinstance(itens, list):
            return [item for item in itens if isinstance(item, dict)]
        return []

    def _enviar(self, method: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        if not self._token:
            raise JurimaiError("JURIMAI_API_TOKEN não configurado.", 503)

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
            logger.warning("Juri+ respondeu %s em %s %s", exc.code, method, path)
            raise JurimaiError(_mensagem_http(exc.code, body), exc.code, body) from exc
        except error.URLError as exc:
            logger.warning("Falha de rede ao chamar Juri+: %s", exc.reason)
            raise JurimaiError("Não foi possível falar com o serviço de acompanhamento.", 504) from exc


def url_de_callback() -> str:
    """URL que a Juri+ recebe em cada monitoramento. O token vai na query porque o aviso não traz assinatura."""
    base = (settings.API_PUBLIC_URL or "").strip().rstrip("/")
    token = (settings.JURIMAI_CALLBACK_TOKEN or "").strip()
    if not base.startswith("https://") or not token:
        raise JurimaiError(
            "O acompanhamento precisa de API_PUBLIC_URL em HTTPS e de JURIMAI_CALLBACK_TOKEN.",
            503,
        )
    prefixo = settings.API_V1_PREFIX.rstrip("/")
    consulta = parse.urlencode({"token": token})
    return f"{base}{prefixo}/integracao/juri/callback?{consulta}"


def monitoramento_existente(itens: list[dict[str, Any]], numero: str) -> dict[str, Any] | None:
    digitos = apenas_digitos(numero)
    for item in itens:
        if str(item.get("tipo") or "") != "processo":
            continue
        if item.get("ativo") is False:
            continue
        if apenas_digitos(str(item.get("alvo") or "")) == digitos and item.get("id"):
            return item
    return None


def _json_ou_vazio(raw: str) -> dict[str, Any]:
    try:
        parsed = json.loads(raw) if raw else {}
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _mensagem_http(status_code: int, body: dict[str, Any]) -> str:
    if status_code == 401:
        return "Token da Juri+ inválido."
    if status_code == 402:
        return "A conta da Juri+ está sem créditos."
    mensagem = body.get("erro") or body.get("message") or body.get("error")
    if isinstance(mensagem, str) and mensagem.strip():
        return mensagem
    return "O serviço de acompanhamento recusou o pedido."
