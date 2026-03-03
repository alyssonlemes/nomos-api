"""
Serviço de Análise de Processos Judiciais.

Implementa todas as funcionalidades descritas no Master Prompt:
- Seção 1: Integração com API DataJud (search_after)
- Seção 2: Filtragem por área jurídica (TPU)
- Seção 3: Cálculo de tempo médio (dataFim inferida de movimentos)
- Seção 4: Preparação de dados para modelo de IA
"""

import json
import time
import urllib.error
import urllib.request
from datetime import date, datetime
from typing import Any, Dict, Iterable, List, Optional, Tuple

import numpy as np
from sqlalchemy import func as sa_func
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.jurimetria_dataset import JurimetriaDataset
from app.schemas.process_analysis import (
    AnaliseEstatisticasFiltro,
    AnaliseEstatisticasResponse,
    AnaliseProcessosFiltro,
    AnaliseProcessosResponse,
    AssuntoInfo,
    ClasseProcessualInfo,
    EstatisticasArea,
    EstatisticasTribunal,
    MovimentoInfo,
    ProcessoAnalisado,
)
from app.services.tpu_mapping import (
    classificar_area_juridica,
    extrair_movimentos_principais,
    identificar_movimento_encerramento,
    obter_codigos_por_area,
)


class ProcessAnalysisService:
    """
    Serviço principal de análise de processos judiciais.

    Responsabilidades:
    1. Coleta de processos via DataJud com paginação search_after
    2. Processamento: inferência de dataFim, classificação de área, cálculo de duração
    3. Persistência no banco com campos enriquecidos
    4. Cálculo de estatísticas agregadas (tempo médio, desvio padrão, percentis)
    """

    RATE_LIMIT_SECONDS = 0.5
    REQUEST_TIMEOUT_SECONDS = 30

    # ──────────────────── 1. Coleta e Análise Principal ───────────────────────

    @staticmethod
    def coletar_e_analisar(
        db: Session,
        filtros: AnaliseProcessosFiltro,
    ) -> AnaliseProcessosResponse:
        """
        Executa coleta de processos do DataJud com análise completa.

        Fluxo:
        1. Monta query DSL com filtros (área, classe, assunto, período)
        2. Pagina via search_after para coleta massiva
        3. Para cada processo:
           - Extrai dataAjuizamento
           - Infere dataFim a partir dos movimentos
           - Calcula duracaoDias
           - Classifica area_juridica_principal
        4. Persiste dados enriquecidos no banco
        5. Calcula estatísticas agregadas
        """
        api_key = settings.DATAJUD_API_KEY
        if not api_key:
            raise ValueError("DATAJUD_API_KEY não configurada no ambiente")

        base_url = f"https://api-publica.datajud.cnj.jus.br/api_publica_{filtros.tribunal_alias}/_search"

        # Resolver códigos TPU se filtro por área
        classe_codigos = []
        assunto_codigos = []
        if filtros.area_juridica:
            codigos = obter_codigos_por_area(filtros.area_juridica)
            classe_codigos = codigos["classes"]
            assunto_codigos = codigos["assuntos"]
        if filtros.classe_codigo:
            classe_codigos = [filtros.classe_codigo]
        if filtros.assunto_codigo:
            assunto_codigos = [filtros.assunto_codigo]

        total_encontrados = 0
        processos: List[ProcessoAnalisado] = []
        search_after_value = None
        pagina = 0
        total_finalizados = 0
        total_em_andamento = 0

        while pagina < filtros.max_paginas:
            # Montar query com search_after (Seção 1.3 do MD)
            if filtros.usar_search_after:
                payload = ProcessAnalysisService._build_search_after_query(
                    filtros=filtros,
                    classe_codigos=classe_codigos,
                    assunto_codigos=assunto_codigos,
                    search_after=search_after_value,
                )
            else:
                payload = ProcessAnalysisService._build_from_size_query(
                    filtros=filtros,
                    classe_codigos=classe_codigos,
                    assunto_codigos=assunto_codigos,
                    offset=pagina * filtros.size,
                )

            response_data = ProcessAnalysisService._post_json(
                url=base_url, api_key=api_key, payload=payload
            )

            # Extrair total na primeira página
            if pagina == 0:
                total_encontrados = ProcessAnalysisService._extract_total(response_data)

            hits = response_data.get("hits", {}).get("hits", [])
            if not hits:
                break

            # Processar hits com análise de movimentos
            page_results, dataset_rows = ProcessAnalysisService._process_hits_with_analysis(
                filtros=filtros,
                hits=hits,
                area_juridica_override=filtros.area_juridica,
            )

            processos.extend(page_results)

            for p in page_results:
                if p.status_processo == "finalizado":
                    total_finalizados += 1
                else:
                    total_em_andamento += 1

            # Persistir
            ProcessAnalysisService._persist_page(
                db=db, tribunal=filtros.tribunal_alias, dataset_rows=dataset_rows
            )

            # Atualizar search_after para próxima página
            if filtros.usar_search_after and hits:
                last_sort = hits[-1].get("sort")
                if last_sort:
                    search_after_value = last_sort
                else:
                    break  # Sem sort value, não dá para continuar

            pagina += 1

            if total_encontrados and len(processos) >= total_encontrados:
                break

            time.sleep(ProcessAnalysisService.RATE_LIMIT_SECONDS)

        # Calcular estatísticas dos processos coletados
        estatisticas = ProcessAnalysisService._calcular_estatisticas_lista(
            processos, filtros.area_juridica or "Geral"
        )

        return AnaliseProcessosResponse(
            total_processos_encontrados=total_encontrados,
            total_processos_processados=len(processos),
            total_finalizados=total_finalizados,
            total_em_andamento=total_em_andamento,
            processos=processos,
            estatisticas=estatisticas,
        )

    # ──────────────────── 2. Estatísticas Agregadas (Seção 4.2) ───────────────

    @staticmethod
    def obter_estatisticas(
        db: Session,
        filtros: AnaliseEstatisticasFiltro,
    ) -> AnaliseEstatisticasResponse:
        """
        Calcula estatísticas agregadas dos processos já persistidos no banco.

        Conforme Seção 4.2 do MD:
        - Tempo médio por área
        - Desvio padrão
        - Percentis (25, 50, 75, 90)
        - Total de processos finalizados e em andamento
        """
        query = db.query(JurimetriaDataset)

        if filtros.tribunal:
            query = query.filter(JurimetriaDataset.tribunal == filtros.tribunal)
        if filtros.area_juridica:
            query = query.filter(
                JurimetriaDataset.area_juridica_principal == filtros.area_juridica
            )

        todos = query.all()

        if not todos:
            return AnaliseEstatisticasResponse(
                total_geral=0,
                total_finalizados=0,
                total_em_andamento=0,
            )

        total_geral = len(todos)
        finalizados = [r for r in todos if r.status_processo == "finalizado"]
        em_andamento = [r for r in todos if r.status_processo != "finalizado"]

        # Estatísticas por área
        areas_dict: Dict[str, List[JurimetriaDataset]] = {}
        for r in todos:
            area = r.area_juridica_principal or "Não classificado"
            areas_dict.setdefault(area, []).append(r)

        estatisticas_por_area = []
        for area_nome, registros in sorted(areas_dict.items()):
            est = ProcessAnalysisService._calcular_estatisticas_registros(
                area_nome, registros
            )
            estatisticas_por_area.append(est)

        # Estatísticas por tribunal
        tribunais_dict: Dict[str, List[JurimetriaDataset]] = {}
        for r in todos:
            tribunais_dict.setdefault(r.tribunal, []).append(r)

        estatisticas_por_tribunal = []
        for trib_nome, registros in sorted(tribunais_dict.items()):
            trib_finalizados = [
                r for r in registros if r.status_processo == "finalizado"
            ]
            trib_andamento = [
                r for r in registros if r.status_processo != "finalizado"
            ]

            # Sub-agrupar por área dentro do tribunal
            trib_areas: Dict[str, List[JurimetriaDataset]] = {}
            for r in registros:
                a = r.area_juridica_principal or "Não classificado"
                trib_areas.setdefault(a, []).append(r)

            areas_trib = [
                ProcessAnalysisService._calcular_estatisticas_registros(a, regs)
                for a, regs in sorted(trib_areas.items())
            ]

            trib_tempo_medio = None
            duracoes_trib = [
                r.duracao_dias for r in trib_finalizados if r.duracao_dias is not None
            ]
            if duracoes_trib:
                trib_tempo_medio = float(np.mean(duracoes_trib))

            estatisticas_por_tribunal.append(
                EstatisticasTribunal(
                    tribunal=trib_nome,
                    total_processos=len(registros),
                    total_finalizados=len(trib_finalizados),
                    total_em_andamento=len(trib_andamento),
                    tempo_medio_dias=trib_tempo_medio,
                    areas=areas_trib,
                )
            )

        return AnaliseEstatisticasResponse(
            total_geral=total_geral,
            total_finalizados=len(finalizados),
            total_em_andamento=len(em_andamento),
            estatisticas_por_area=estatisticas_por_area,
            estatisticas_por_tribunal=estatisticas_por_tribunal,
        )

    # ──────────────────── Query Builders ──────────────────────────────────────

    @staticmethod
    def _build_search_after_query(
        filtros: AnaliseProcessosFiltro,
        classe_codigos: List[str],
        assunto_codigos: List[str],
        search_after: Optional[List] = None,
    ) -> Dict[str, Any]:
        """
        Constrói query DSL com paginação search_after (Seção 1.3 do MD).

        search_after permite paginar além do limite de 10.000 resultados,
        crucial para coleta massiva de processos.
        """
        filters = ProcessAnalysisService._build_filters(
            filtros, classe_codigos, assunto_codigos
        )

        query: Dict[str, Any] = {
            "size": filtros.size,
            "track_total_hits": True,
            "sort": [
                {"@timestamp": {"order": "asc"}},
                {"numeroProcesso.keyword": {"order": "asc"}},
            ],
            "query": {"bool": {"filter": filters}},
        }

        if search_after:
            query["search_after"] = search_after

        return query

    @staticmethod
    def _build_from_size_query(
        filtros: AnaliseProcessosFiltro,
        classe_codigos: List[str],
        assunto_codigos: List[str],
        offset: int = 0,
    ) -> Dict[str, Any]:
        """Query com paginação from/size (fallback, limite 10k)."""
        filters = ProcessAnalysisService._build_filters(
            filtros, classe_codigos, assunto_codigos
        )

        return {
            "from": offset,
            "size": filtros.size,
            "track_total_hits": True,
            "sort": [
                {"dataAjuizamento": {"order": "asc"}},
                {"numeroProcesso.keyword": {"order": "asc"}},
            ],
            "query": {"bool": {"filter": filters}},
        }

    @staticmethod
    def _to_int(value: str) -> int:
        """Converte código TPU string para inteiro (DataJud exige numérico)."""
        try:
            return int(value)
        except (ValueError, TypeError):
            return 0

    @staticmethod
    def _build_filters(
        filtros: AnaliseProcessosFiltro,
        classe_codigos: List[str],
        assunto_codigos: List[str],
    ) -> List[Dict[str, Any]]:
        """Constrói array de filtros para a query DSL (Seção 2.3 do MD)."""
        filters: List[Dict[str, Any]] = []

        # Filtro por período de ajuizamento
        if filtros.data_inicio or filtros.data_fim:
            range_filter: Dict[str, Any] = {}
            if filtros.data_inicio:
                range_filter["gte"] = filtros.data_inicio.isoformat()
            if filtros.data_fim:
                range_filter["lte"] = filtros.data_fim.isoformat()
            filters.append({"range": {"dataAjuizamento": range_filter}})

        # Filtro por classe processual e/ou assunto (Seção 2.1)
        # Usa query `terms` (Elasticsearch plural) — muito mais eficiente
        # e compatível com a API DataJud do que bool/should/term aninhado.
        # Quando ambos são fornecidos, usa OR entre classes e assuntos
        # (um processo Criminal pode ter classe criminal OU assunto criminal).
        int_classes = []
        int_assuntos = []

        if classe_codigos:
            int_classes = [ProcessAnalysisService._to_int(c) for c in classe_codigos if c]
            int_classes = [c for c in int_classes if c > 0]

        if assunto_codigos:
            int_assuntos = [ProcessAnalysisService._to_int(c) for c in assunto_codigos if c]
            int_assuntos = [c for c in int_assuntos if c > 0]

        if int_classes and int_assuntos:
            # OR: processo que tenha classe OU assunto da área
            filters.append(
                {
                    "bool": {
                        "should": [
                            {"terms": {"classe.codigo": int_classes}},
                            {"terms": {"assuntos.codigo": int_assuntos}},
                        ],
                        "minimum_should_match": 1,
                    }
                }
            )
        elif int_classes:
            filters.append({"terms": {"classe.codigo": int_classes}})
        elif int_assuntos:
            filters.append({"terms": {"assuntos.codigo": int_assuntos}})

        return filters

    # ──────────────────── Processamento de Hits (Seções 3 e 4) ────────────────

    @staticmethod
    def _process_hits_with_analysis(
        filtros: AnaliseProcessosFiltro,
        hits: Iterable[Dict[str, Any]],
        area_juridica_override: Optional[str] = None,
    ) -> Tuple[List[ProcessoAnalisado], List[JurimetriaDataset]]:
        """
        Processa hits do DataJud com análise completa.

        Para cada processo:
        1. Extrai dataAjuizamento (Seção 3.1)
        2. Analisa movimentos para inferir dataFim (Seção 3.2)
        3. Calcula duração em dias (Seção 3.3)
        4. Classifica área jurídica (Seção 2)
        5. Monta estrutura conforme Seção 4.1
        """
        processos: List[ProcessoAnalisado] = []
        dataset_rows: List[JurimetriaDataset] = []

        for hit in hits:
            source = hit.get("_source", {}) or {}

            # Extrair número do processo
            numero_processo = (
                source.get("numeroProcesso")
                or source.get("numero_processo")
                or source.get("numeroProcessoCNJ")
            )
            if not numero_processo:
                continue

            # Seção 3.1: Data de Início
            data_ajuizamento = ProcessAnalysisService._parse_date(
                source.get("dataAjuizamento")
            )
            if not data_ajuizamento:
                continue

            # Extrair classe processual
            classe_raw = source.get("classe") or source.get("classeProcessual") or {}
            classe_codigo = None
            classe_nome = None
            if isinstance(classe_raw, dict):
                classe_codigo = str(classe_raw.get("codigo", ""))
                classe_nome = classe_raw.get("nome")
            elif isinstance(classe_raw, str):
                classe_codigo = classe_raw

            # Extrair assuntos
            assuntos_raw = source.get("assuntos") or source.get("assunto") or []
            assuntos_info: List[AssuntoInfo] = []
            assunto_codigos_list: List[str] = []

            if isinstance(assuntos_raw, list):
                for ass in assuntos_raw:
                    if isinstance(ass, dict):
                        cod = str(ass.get("codigo", ""))
                        nome = ass.get("nome")
                        assuntos_info.append(AssuntoInfo(codigo=cod, nome=nome))
                        if cod:
                            assunto_codigos_list.append(cod)
                    elif isinstance(ass, str):
                        assuntos_info.append(AssuntoInfo(codigo=ass))
                        assunto_codigos_list.append(ass)

            # Seção 2: Classificar área jurídica pelo código real do processo
            # Não usa override — cada processo é classificado individualmente
            area_juridica = classificar_area_juridica(
                classe_codigo=classe_codigo,
                assunto_codigos=assunto_codigos_list or None,
            )
            if not area_juridica:
                area_juridica = area_juridica_override or "Não classificado"

            # Seção 3.2: Inferir dataFim a partir dos movimentos
            movimentos = source.get("movimentos") or source.get("movimentacoes") or []
            mov_encerramento = identificar_movimento_encerramento(movimentos)

            data_fim = None
            status_processo = "em_andamento"
            movimento_enc_nome = None
            duracao_dias = None

            if mov_encerramento:
                data_fim = ProcessAnalysisService._parse_date(
                    mov_encerramento.get("dataHora")
                )
                status_processo = "finalizado"
                movimento_enc_nome = mov_encerramento.get("nome")

                # Seção 3.3: Calcular duração
                if data_fim and data_ajuizamento:
                    duracao_dias = (data_fim - data_ajuizamento).days

            # Movimentos principais simplificados
            movimentos_principais = [
                MovimentoInfo(**m)
                for m in extrair_movimentos_principais(movimentos)
            ]

            # Seção 4.1: Montar estrutura de saída
            processo = ProcessoAnalisado(
                numero_processo=str(numero_processo),
                tribunal=filtros.tribunal_alias,
                area_juridica_principal=area_juridica,
                classe_principal=ClasseProcessualInfo(
                    codigo=classe_codigo,
                    nome=classe_nome,
                ),
                assuntos_relacionados=assuntos_info,
                data_ajuizamento=data_ajuizamento,
                data_fim=data_fim,
                duracao_dias=duracao_dias,
                status_processo=status_processo,
                movimento_encerramento=movimento_enc_nome,
                movimentos_principais=movimentos_principais,
            )
            processos.append(processo)

            # Row para persistência
            assuntos_json_str = None
            if assuntos_info:
                assuntos_json_str = json.dumps(
                    [a.model_dump() for a in assuntos_info],
                    ensure_ascii=False,
                )

            dataset_rows.append(
                JurimetriaDataset(
                    tribunal=filtros.tribunal_alias,
                    numero_processo=str(numero_processo),
                    data_ajuizamento=data_ajuizamento,
                    classe_processual=classe_codigo,
                    assunto_codigo=assunto_codigos_list[0] if assunto_codigos_list else None,
                    area_juridica_principal=area_juridica,
                    classe_principal_nome=classe_nome,
                    assuntos_json=assuntos_json_str,
                    data_fim=data_fim,
                    status_processo=status_processo,
                    movimento_encerramento=movimento_enc_nome,
                    duracao_dias=duracao_dias,
                )
            )

        return processos, dataset_rows

    # ──────────────────── Persistência ────────────────────────────────────────

    @staticmethod
    def _persist_page(
        db: Session,
        tribunal: str,
        dataset_rows: List[JurimetriaDataset],
    ) -> None:
        """Persiste ou atualiza os dados no banco."""
        if not dataset_rows:
            return

        numeros = [row.numero_processo for row in dataset_rows]
        existing = (
            db.query(JurimetriaDataset.numero_processo)
            .filter(
                JurimetriaDataset.tribunal == tribunal,
                JurimetriaDataset.numero_processo.in_(numeros),
            )
            .all()
        )
        existing_numbers = {item[0] for item in existing}

        rows_to_insert = []
        rows_to_update = []

        for row in dataset_rows:
            if row.numero_processo in existing_numbers:
                rows_to_update.append(row)
            else:
                rows_to_insert.append(row)

        try:
            # Inserir novos
            if rows_to_insert:
                db.add_all(rows_to_insert)

            # Atualizar existentes com campos novos
            for row in rows_to_update:
                db.query(JurimetriaDataset).filter(
                    JurimetriaDataset.tribunal == tribunal,
                    JurimetriaDataset.numero_processo == row.numero_processo,
                ).update(
                    {
                        "area_juridica_principal": row.area_juridica_principal,
                        "classe_principal_nome": row.classe_principal_nome,
                        "assuntos_json": row.assuntos_json,
                        "data_fim": row.data_fim,
                        "status_processo": row.status_processo,
                        "movimento_encerramento": row.movimento_encerramento,
                        "duracao_dias": row.duracao_dias,
                    }
                )

            db.commit()
        except Exception as exc:
            db.rollback()
            raise RuntimeError("Erro ao persistir dados de análise") from exc

    # ──────────────────── Cálculos Estatísticos (Seção 4.2) ───────────────────

    @staticmethod
    def _calcular_estatisticas_lista(
        processos: List[ProcessoAnalisado],
        area: str,
    ) -> EstatisticasArea:
        """Calcula estatísticas a partir de uma lista de ProcessoAnalisado."""
        finalizados = [p for p in processos if p.status_processo == "finalizado"]
        em_andamento = [p for p in processos if p.status_processo != "finalizado"]
        duracoes = [
            p.duracao_dias for p in finalizados if p.duracao_dias is not None
        ]

        return ProcessAnalysisService._calcular_estatisticas_from_duracoes(
            area=area,
            duracoes=duracoes,
            total_finalizados=len(finalizados),
            total_em_andamento=len(em_andamento),
        )

    @staticmethod
    def _calcular_estatisticas_registros(
        area: str,
        registros: List[JurimetriaDataset],
    ) -> EstatisticasArea:
        """Calcula estatísticas a partir de registros do banco."""
        finalizados = [r for r in registros if r.status_processo == "finalizado"]
        em_andamento = [r for r in registros if r.status_processo != "finalizado"]
        duracoes = [
            r.duracao_dias for r in finalizados if r.duracao_dias is not None
        ]

        return ProcessAnalysisService._calcular_estatisticas_from_duracoes(
            area=area,
            duracoes=duracoes,
            total_finalizados=len(finalizados),
            total_em_andamento=len(em_andamento),
        )

    @staticmethod
    def _calcular_estatisticas_from_duracoes(
        area: str,
        duracoes: List[int],
        total_finalizados: int,
        total_em_andamento: int,
    ) -> EstatisticasArea:
        """
        Calcula tempo médio, desvio padrão e percentis.

        Conforme Seção 4.2 do MD:
        - tempoMedioDias
        - desvioPadraoDias
        - percentil25Dias, percentil50Dias, percentil75Dias
        """
        if not duracoes:
            return EstatisticasArea(
                area=area,
                total_processos_finalizados=total_finalizados,
                total_processos_em_andamento=total_em_andamento,
            )

        arr = np.array(duracoes)

        return EstatisticasArea(
            area=area,
            tempo_medio_dias=round(float(np.mean(arr)), 2),
            desvio_padrao_dias=round(float(np.std(arr)), 2),
            total_processos_finalizados=total_finalizados,
            total_processos_em_andamento=total_em_andamento,
            percentil_25_dias=round(float(np.percentile(arr, 25)), 2),
            percentil_50_dias=round(float(np.percentile(arr, 50)), 2),
            percentil_75_dias=round(float(np.percentile(arr, 75)), 2),
            percentil_90_dias=round(float(np.percentile(arr, 90)), 2),
            duracao_minima_dias=int(np.min(arr)),
            duracao_maxima_dias=int(np.max(arr)),
        )

    # ──────────────────── HTTP Client ─────────────────────────────────────────

    @staticmethod
    def _post_json(
        url: str, api_key: str, payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Executa POST na API DataJud (Seção 1.2 do MD)."""
        data = json.dumps(payload).encode("utf-8")
        headers = {
            "Authorization": f"ApiKey {api_key}",
            "Content-Type": "application/json",
        }
        request = urllib.request.Request(
            url, data=data, headers=headers, method="POST"
        )

        try:
            with urllib.request.urlopen(
                request, timeout=ProcessAnalysisService.REQUEST_TIMEOUT_SECONDS
            ) as response:
                body = response.read().decode("utf-8")
                return json.loads(body)
        except urllib.error.HTTPError as exc:
            error_body = exc.read().decode("utf-8") if exc.fp else ""
            raise RuntimeError(
                f"Erro DataJud: HTTP {exc.code} - {error_body}"
            ) from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(
                f"Erro de conexão com DataJud: {exc.reason}"
            ) from exc
        except json.JSONDecodeError as exc:
            raise RuntimeError("Resposta inválida do DataJud") from exc

    @staticmethod
    def _extract_total(response_data: Dict[str, Any]) -> int:
        """Extrai total de hits da resposta."""
        total = response_data.get("hits", {}).get("total", 0)
        if isinstance(total, dict):
            return int(total.get("value", 0))
        if isinstance(total, int):
            return total
        return 0

    # ──────────────────── Utilitários ─────────────────────────────────────────

    @staticmethod
    def _parse_date(value: Optional[Any]) -> Optional[date]:
        """Parse flexível de datas vindas da API DataJud."""
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
                pass
            # Tentar outros formatos comuns
            for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y-%m-%dT%H:%M:%S"):
                try:
                    return datetime.strptime(value, fmt).date()
                except ValueError:
                    continue
        return None
