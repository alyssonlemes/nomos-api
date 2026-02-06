import json
import os
import time
import urllib.error
import urllib.request
from datetime import date, datetime
from typing import Any, Dict, Iterable, List, Optional, Tuple

from sqlalchemy.orm import Session

from app.models.jurimetria_dataset import JurimetriaDataset
from app.schemas.jurimetria_batch import BatchFiltroRequest, BatchResponse, ProcessoBatchResult


class DataJudBatchService:
    """
    Serviço para coleta em lote via DataJud (CNJ) com persistência e normalização
    """

    RATE_LIMIT_SECONDS = 0.5
    REQUEST_TIMEOUT_SECONDS = 30

    @staticmethod
    def run_batch(db: Session, filtros: BatchFiltroRequest) -> BatchResponse:
        api_key = os.getenv("DATAJUD_API_KEY")
        if not api_key:
            raise ValueError("DATAJUD_API_KEY não configurada no ambiente")

        base_url = f"https://api-publica.datajud.cnj.jus.br/api_publica_{filtros.tribunal_alias}/_search"
        size = filtros.size or 100
        offset = 0

        total_processos = 0
        processos_processados = 0
        resultados: List[ProcessoBatchResult] = []

        while True:
            payload = DataJudBatchService._build_query(filtros=filtros, size=size, offset=offset)
            response_data = DataJudBatchService._post_json(url=base_url, api_key=api_key, payload=payload)

            hits = response_data.get("hits", {}).get("hits", [])
            if total_processos == 0:
                total_processos = DataJudBatchService._extract_total(response_data)

            if not hits:
                break

            page_results, dataset_rows = DataJudBatchService._process_hits(filtros, hits)
            resultados.extend(page_results)
            processos_processados += len(page_results)

            DataJudBatchService._persist_page(db=db, filtros=filtros, dataset_rows=dataset_rows)

            offset += size
            if total_processos and offset >= total_processos:
                break

            time.sleep(DataJudBatchService.RATE_LIMIT_SECONDS)

        # Ponto de extensão futura: feature engineering para construção de variáveis
        # Ponto de extensão futura: treinamento e validação de modelos
        # Ponto de extensão futura: versionamento e tracking de modelos

        return BatchResponse(
            total_processos=total_processos,
            processos_processados=processos_processados,
            resultados=resultados
        )

    @staticmethod
    def _build_query(filtros: BatchFiltroRequest, size: int, offset: int) -> Dict[str, Any]:
        filters: List[Dict[str, Any]] = [
            {
                "range": {
                    "dataAjuizamento": {
                        "gte": filtros.data_inicio.isoformat(),
                        "lte": filtros.data_fim.isoformat()
                    }
                }
            }
        ]

        if filtros.classe_processual:
            filters.append({"term": {"classeProcessual": filtros.classe_processual}})

        if filtros.assunto_codigo:
            filters.append({"term": {"assuntos.codigo": filtros.assunto_codigo}})

        return {
            "from": offset,
            "size": size,
            "track_total_hits": True,
            "sort": [
                {"dataAjuizamento": {"order": "asc"}},
                {"numeroProcesso.keyword": {"order": "asc"}}
            ],
            "query": {
                "bool": {
                    "filter": filters
                }
            }
        }

    @staticmethod
    def _post_json(url: str, api_key: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        data = json.dumps(payload).encode("utf-8")
        headers = {
            "Authorization": f"ApiKey {api_key}",
            "Content-Type": "application/json"
        }
        request = urllib.request.Request(url, data=data, headers=headers, method="POST")

        try:
            with urllib.request.urlopen(request, timeout=DataJudBatchService.REQUEST_TIMEOUT_SECONDS) as response:
                body = response.read().decode("utf-8")
                return json.loads(body)
        except urllib.error.HTTPError as exc:
            error_body = exc.read().decode("utf-8") if exc.fp else ""
            raise RuntimeError(f"Erro DataJud: HTTP {exc.code} - {error_body}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Erro de conexão com DataJud: {exc.reason}") from exc
        except json.JSONDecodeError as exc:
            raise RuntimeError("Resposta inválida do DataJud") from exc

    @staticmethod
    def _extract_total(response_data: Dict[str, Any]) -> int:
        total = response_data.get("hits", {}).get("total", 0)
        if isinstance(total, dict):
            return int(total.get("value", 0))
        if isinstance(total, int):
            return total
        return 0

    @staticmethod
    def _process_hits(
        filtros: BatchFiltroRequest,
        hits: Iterable[Dict[str, Any]]
    ) -> Tuple[List[ProcessoBatchResult], List[JurimetriaDataset]]:
        resultados: List[ProcessoBatchResult] = []
        dataset_rows: List[JurimetriaDataset] = []

        for hit in hits:
            source = hit.get("_source", {}) or {}

            numero_processo = (
                source.get("numeroProcesso")
                or source.get("numero_processo")
                or source.get("numeroProcessoCNJ")
            )

            data_ajuizamento = DataJudBatchService._parse_date(source.get("dataAjuizamento"))
            if not numero_processo or not data_ajuizamento:
                continue

            data_ultima_movimentacao = DataJudBatchService._parse_date(
                source.get("dataUltimaMovimentacao")
                or source.get("dataUltimoMovimento")
                or source.get("dataUltimaMovimentacaoProcessual")
            )

            tempo_tramitacao_dias = DataJudBatchService._calc_tempo_tramitacao(
                data_ajuizamento,
                data_ultima_movimentacao
            )

            classe_processual = DataJudBatchService._extract_text_or_code(source.get("classeProcessual"))
            assunto_codigo = DataJudBatchService._extract_assunto_codigo(source.get("assuntos") or source.get("assunto"))

            resultados.append(
                ProcessoBatchResult(
                    numero_processo=str(numero_processo),
                    data_ajuizamento=data_ajuizamento,
                    data_ultima_movimentacao=data_ultima_movimentacao,
                    tempo_tramitacao_dias=tempo_tramitacao_dias
                )
            )

            dataset_rows.append(
                JurimetriaDataset(
                    tribunal=filtros.tribunal_alias,
                    numero_processo=str(numero_processo),
                    data_ajuizamento=data_ajuizamento,
                    data_ultima_movimentacao=data_ultima_movimentacao,
                    tempo_tramitacao_dias=tempo_tramitacao_dias,
                    classe_processual=classe_processual or filtros.classe_processual,
                    assunto_codigo=assunto_codigo or filtros.assunto_codigo
                )
            )

        return resultados, dataset_rows

    @staticmethod
    def _persist_page(db: Session, filtros: BatchFiltroRequest, dataset_rows: List[JurimetriaDataset]) -> None:
        if not dataset_rows:
            return

        numeros = [row.numero_processo for row in dataset_rows]
        existing = db.query(JurimetriaDataset.numero_processo).filter(
            JurimetriaDataset.tribunal == filtros.tribunal_alias,
            JurimetriaDataset.numero_processo.in_(numeros)
        ).all()
        existing_numbers = {item[0] for item in existing}

        rows_to_insert = [row for row in dataset_rows if row.numero_processo not in existing_numbers]
        if not rows_to_insert:
            return

        try:
            db.add_all(rows_to_insert)
            db.commit()
        except Exception as exc:
            db.rollback()
            raise RuntimeError("Erro ao persistir dados de jurimetria") from exc

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
    def _calc_tempo_tramitacao(data_ajuizamento: date, data_ultima: Optional[date]) -> Optional[int]:
        if not data_ajuizamento or not data_ultima:
            return None
        return (data_ultima - data_ajuizamento).days

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
