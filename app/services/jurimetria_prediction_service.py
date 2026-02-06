import json
import os
import urllib.error
import urllib.request
from datetime import date, datetime
from typing import Any, Dict, Optional

import pandas as pd

from app.ml.features import build_inference_matrix
from app.ml.model_registry import load_active_model
from app.schemas.jurimetria_prediction import JurimetriaPredictionResponse


class JurimetriaPredictionService:
    """
    Serviço de predição de tempo de tramitação para processos existentes no DataJud.
    """

    REQUEST_TIMEOUT_SECONDS = 30

    @staticmethod
    def predict(tribunal: str, numero_processo: str) -> JurimetriaPredictionResponse:
        api_key = os.getenv("DATAJUD_API_KEY")
        if not api_key:
            raise ValueError("DATAJUD_API_KEY não configurada no ambiente")

        model, metadata = load_active_model()
        if not model or not metadata:
            raise RuntimeError("Modelo ativo não encontrado")

        feature_columns = metadata.get("feature_columns")
        if not feature_columns:
            raise RuntimeError("Modelo ativo não possui metadata de features")

        process_data = JurimetriaPredictionService._fetch_process_data(
            api_key=api_key,
            tribunal=tribunal,
            numero_processo=numero_processo
        )

        if not process_data:
            raise FileNotFoundError("Processo não encontrado no DataJud")

        features_input = JurimetriaPredictionService._normalize_for_features(
            tribunal=tribunal,
            process_data=process_data
        )

        if not features_input.get("data_ajuizamento"):
            raise ValueError("Dados insuficientes para predição: data_ajuizamento ausente")

        X = build_inference_matrix(features_input, feature_columns)

        prediction = float(model.predict(X)[0])
        tempo_total_estimado_dias = max(int(round(prediction)), 0)

        data_ajuizamento = features_input.get("data_ajuizamento")
        tempo_decorrido_dias = JurimetriaPredictionService._calc_tempo_decorrido(data_ajuizamento)

        tempo_estimado_restante_dias = None
        if tempo_decorrido_dias is not None:
            tempo_estimado_restante_dias = max(tempo_total_estimado_dias - tempo_decorrido_dias, 0)

        return JurimetriaPredictionResponse(
            numero_processo=numero_processo,
            tribunal=tribunal,
            tempo_total_estimado_dias=tempo_total_estimado_dias,
            tempo_decorrido_dias=tempo_decorrido_dias,
            tempo_estimado_restante_dias=tempo_estimado_restante_dias,
            fonte_dados="DataJud"
        )

    @staticmethod
    def _fetch_process_data(api_key: str, tribunal: str, numero_processo: str) -> Optional[Dict[str, Any]]:
        url = f"https://api-publica.datajud.cnj.jus.br/api_publica_{tribunal}/_search"
        payload = {
            "size": 1,
            "query": {
                "bool": {
                    "must": [
                        {"term": {"numeroProcesso.keyword": numero_processo}}
                    ]
                }
            }
        }

        data = json.dumps(payload).encode("utf-8")
        headers = {
            "Authorization": f"ApiKey {api_key}",
            "Content-Type": "application/json"
        }
        request = urllib.request.Request(url, data=data, headers=headers, method="POST")

        try:
            with urllib.request.urlopen(request, timeout=JurimetriaPredictionService.REQUEST_TIMEOUT_SECONDS) as response:
                body = response.read().decode("utf-8")
                response_data = json.loads(body)
                hits = response_data.get("hits", {}).get("hits", [])
                if not hits:
                    return None
                return hits[0].get("_source") or {}
        except urllib.error.HTTPError as exc:
            error_body = exc.read().decode("utf-8") if exc.fp else ""
            raise RuntimeError(f"Erro DataJud: HTTP {exc.code} - {error_body}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Erro de conexão com DataJud: {exc.reason}") from exc
        except json.JSONDecodeError as exc:
            raise RuntimeError("Resposta inválida do DataJud") from exc

    @staticmethod
    def _normalize_for_features(tribunal: str, process_data: Dict[str, Any]) -> Dict[str, Any]:
        classe_processual = JurimetriaPredictionService._extract_text_or_code(
            process_data.get("classeProcessual")
        )
        assunto_codigo = JurimetriaPredictionService._extract_assunto_codigo(
            process_data.get("assuntos") or process_data.get("assunto")
        )

        data_ajuizamento = JurimetriaPredictionService._parse_date(process_data.get("dataAjuizamento"))

        return {
            "tribunal": tribunal,
            "classe_processual": classe_processual,
            "assunto_codigo": assunto_codigo,
            "data_ajuizamento": data_ajuizamento
        }

    @staticmethod
    def _parse_date(value: Optional[Any]) -> Optional[date]:
        if not value:
            return None
        if isinstance(value, date) and not isinstance(value, datetime):
            return value
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, str):
            try:
                normalized = value.replace("Z", "+00:00")
                return datetime.fromisoformat(normalized).date()
            except ValueError:
                return None
        return None

    @staticmethod
    def _calc_tempo_decorrido(data_ajuizamento: date) -> Optional[int]:
        if not data_ajuizamento:
            return None
        return (date.today() - data_ajuizamento).days

    @staticmethod
    def _extract_text_or_code(value: Any) -> Optional[str]:
        if value is None:
            return None
        if isinstance(value, str):
            return value
        if isinstance(value, dict):
            return str(value.get("codigo") or value.get("nome") or "") or None
        return str(value) if value else None

    @staticmethod
    def _extract_assunto_codigo(value: Any) -> Optional[str]:
        if value is None:
            return None
        if isinstance(value, list) and value:
            first = value[0]
            if isinstance(first, dict):
                return str(first.get("codigo") or "") or None
            if isinstance(first, str):
                return first
        if isinstance(value, dict):
            return str(value.get("codigo") or "") or None
        if isinstance(value, str):
            return value
        return None
