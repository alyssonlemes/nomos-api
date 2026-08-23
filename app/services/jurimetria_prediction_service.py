import json
import logging
import os
import re
import urllib.error
import urllib.request
from datetime import date, datetime
from typing import Any, Dict, Optional, Tuple

import pandas as pd

from app.core.config import settings
from app.schemas.jurimetria_prediction import JurimetriaPredictionResponse

logger = logging.getLogger(__name__)


class JurimetriaPredictionService:
    """
    Serviço de predição de tempo de tramitação para processos existentes no DataJud.
    """

    REQUEST_TIMEOUT_SECONDS = 15

    REQUIRED_CHAT_FIELDS = ("tribunal", "data_ajuizamento")

    @staticmethod
    def predict(tribunal: str, numero_processo: str) -> JurimetriaPredictionResponse:
        # Lazy imports to avoid loading sklearn at startup
        from app.ml.features import build_inference_matrix
        from app.ml.model_registry import load_active_model
        
        api_key = settings.DATAJUD_API_KEY
        if not api_key:
            raise RuntimeError("DATAJUD_API_KEY não configurada no ambiente")

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
        data_fim = features_input.get("data_fim")
        tempo_decorrido_dias = JurimetriaPredictionService._calc_tempo_decorrido(data_ajuizamento, data_fim)

        tempo_estimado_restante_dias = None
        if tempo_decorrido_dias is not None:
            tempo_estimado_restante_dias = max(tempo_total_estimado_dias - tempo_decorrido_dias, 0)

        status = "finalizado" if data_fim else "em_andamento"
        if status == "finalizado":
            tempo_estimado_restante_dias = 0

        return JurimetriaPredictionResponse(
            numero_processo=numero_processo,
            tribunal=tribunal,
            tempo_total_estimado_dias=tempo_total_estimado_dias,
            tempo_decorrido_dias=tempo_decorrido_dias,
            tempo_estimado_restante_dias=tempo_estimado_restante_dias,
            status=status,
            fonte_dados="DataJud"
        )

    @staticmethod
    def predict_from_features(
        tribunal: str,
        classe_processual: Optional[str],
        area_juridica_principal: Optional[str],
        data_ajuizamento: date,
    ) -> Dict[str, Any]:
        from app.ml.features import build_inference_matrix
        from app.ml.model_registry import load_active_model

        model, metadata = load_active_model()
        if not model or not metadata:
            raise RuntimeError("Modelo ativo não encontrado")

        feature_columns = metadata.get("feature_columns")
        if not feature_columns:
            raise RuntimeError("Modelo ativo não possui metadata de features")

        features_input = {
            "tribunal": tribunal,
            "classe_processual": classe_processual,
            "area_juridica_principal": area_juridica_principal,
            "data_ajuizamento": data_ajuizamento,
        }

        X = build_inference_matrix(features_input, feature_columns)
        prediction = float(model.predict(X)[0])
        tempo_total_estimado_dias = max(int(round(prediction)), 0)

        tempo_decorrido_dias = JurimetriaPredictionService._calc_tempo_decorrido(data_ajuizamento)
        tempo_estimado_restante_dias = None
        if tempo_decorrido_dias is not None:
            tempo_estimado_restante_dias = max(tempo_total_estimado_dias - tempo_decorrido_dias, 0)

        return {
            "tribunal": tribunal,
            "classe_processual": classe_processual,
            "area_juridica_principal": area_juridica_principal,
            "data_ajuizamento": data_ajuizamento,
            "tempo_total_estimado_dias": tempo_total_estimado_dias,
            "tempo_decorrido_dias": tempo_decorrido_dias,
            "tempo_estimado_restante_dias": tempo_estimado_restante_dias,
            "fonte_dados": "Manual",
        }

    @staticmethod
    def parse_chat_message(
        message: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Tuple[Dict[str, Any], list[str]]:
        data: Dict[str, Any] = {**(context or {})}
        lowered = message.lower()

        if not data.get("tribunal"):
            tribunal_match = re.search(r"\b(tj[a-z]{2,3})\b", lowered)
            if tribunal_match:
                data["tribunal"] = tribunal_match.group(1)

        if not data.get("data_ajuizamento"):
            date_match = re.search(r"(\d{4}-\d{2}-\d{2})", lowered)
            if not date_match:
                date_match = re.search(r"(\d{2})[/-](\d{2})[/-](\d{4})", lowered)
                if date_match:
                    day, month, year = date_match.groups()
                    data["data_ajuizamento"] = date(int(year), int(month), int(day))
            else:
                try:
                    data["data_ajuizamento"] = date.fromisoformat(date_match.group(1))
                except ValueError:
                    pass

        if not data.get("area_juridica_principal"):
            area_match = re.search(
                r"area(?:_juridica(?:_principal)?)?\s*[:=]\s*([^\n\r;,.]+)",
                message,
                re.IGNORECASE,
            )
            if area_match:
                data["area_juridica_principal"] = area_match.group(1).strip()

        if not data.get("classe_processual"):
            classe_match = re.search(
                r"classe(?:_processual)?\s*[:=]\s*([^\n\r;,.]+)",
                message,
                re.IGNORECASE,
            )
            if classe_match:
                data["classe_processual"] = classe_match.group(1).strip()

        missing = [field for field in JurimetriaPredictionService.REQUIRED_CHAT_FIELDS if not data.get(field)]
        return data, missing

    @staticmethod
    def _fetch_process_data(api_key: str, tribunal: str, numero_processo: str) -> Optional[Dict[str, Any]]:
        url = f"https://api-publica.datajud.cnj.jus.br/api_publica_{tribunal}/_search"
        limpo = re.sub(r"\D", "", numero_processo)
        should_clauses = [
            {"term": {"numeroProcesso.keyword": numero_processo}},
            {"term": {"numeroProcesso": numero_processo}},
        ]
        if limpo:
            should_clauses.extend([
                {"term": {"numeroProcesso.keyword": limpo}},
                {"term": {"numeroProcesso": limpo}},
            ])

        payload = {
            "size": 1,
            "query": {
                "bool": {
                    "should": should_clauses,
                    "minimum_should_match": 1,
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
            logger.error("DataJud HTTPError %s para %s/%s: %s", exc.code, tribunal, numero_processo, error_body)
            raise RuntimeError(f"Erro DataJud: HTTP {exc.code} - {error_body}") from exc
        except urllib.error.URLError as exc:
            logger.error("DataJud URLError para %s/%s: %s", tribunal, numero_processo, exc.reason)
            raise RuntimeError(f"Erro de conexão com DataJud: {exc.reason}") from exc
        except (TimeoutError, OSError) as exc:
            logger.error("DataJud timeout/OSError para %s/%s: %s", tribunal, numero_processo, exc)
            raise RuntimeError(f"Timeout ao conectar com DataJud: {exc}") from exc
        except json.JSONDecodeError as exc:
            logger.error("DataJud resposta inválida para %s/%s", tribunal, numero_processo)
            raise RuntimeError("Resposta inválida do DataJud") from exc

    @staticmethod
    def _normalize_for_features(tribunal: str, process_data: Dict[str, Any]) -> Dict[str, Any]:
        from app.services.tpu_mapping import classificar_area_juridica, identificar_movimento_encerramento

        classe_processual = JurimetriaPredictionService._extract_text_or_code(
            process_data.get("classeProcessual") or process_data.get("classe")
        )
        assunto_codigo = JurimetriaPredictionService._extract_assunto_codigo(
            process_data.get("assuntos") or process_data.get("assunto")
        )

        assunto_codigos = [assunto_codigo] if assunto_codigo else None
        area_juridica_principal = classificar_area_juridica(
            classe_codigo=classe_processual,
            assunto_codigos=assunto_codigos
        )

        raw_date = (
            process_data.get("dataAjuizamento")
            or process_data.get("dataHoraDistribuicao")
            or process_data.get("dataDistribuicao")
        )
        data_ajuizamento = JurimetriaPredictionService._parse_date(raw_date)

        movimentos = process_data.get("movimentos") or process_data.get("movimentacoes") or []
        mov_encerramento = identificar_movimento_encerramento(movimentos)
        data_fim = None
        if mov_encerramento:
            data_fim = JurimetriaPredictionService._parse_date(mov_encerramento.get("dataHora"))

        return {
            "tribunal": tribunal,
            "classe_processual": classe_processual,
            "assunto_codigo": assunto_codigo,
            "area_juridica_principal": area_juridica_principal,
            "data_ajuizamento": data_ajuizamento,
            "data_fim": data_fim
        }

    @staticmethod
    def _parse_date(value: Optional[Any]) -> Optional[date]:
        if not value:
            return None
        if isinstance(value, date) and not isinstance(value, datetime):
            return value
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, (int, float)):
            value = str(int(value))
        if isinstance(value, str):
            value = value.strip()
            if not value:
                return None
            try:
                normalized = value.replace("Z", "+00:00")
                return datetime.fromisoformat(normalized).date()
            except ValueError:
                pass
            if value.isdigit():
                if len(value) >= 14:
                    try:
                        return datetime.strptime(value[:14], "%Y%m%d%H%M%S").date()
                    except ValueError:
                        pass
                if len(value) >= 8:
                    try:
                        return datetime.strptime(value[:8], "%Y%m%d").date()
                    except ValueError:
                        pass
            for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"):
                try:
                    return datetime.strptime(value, fmt).date()
                except ValueError:
                    continue
        return None

    @staticmethod
    def _calc_tempo_decorrido(data_ajuizamento: date, data_fim: Optional[date] = None) -> Optional[int]:
        if not data_ajuizamento:
            return None
        end_date = data_fim if data_fim else date.today()
        return (end_date - data_ajuizamento).days

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
