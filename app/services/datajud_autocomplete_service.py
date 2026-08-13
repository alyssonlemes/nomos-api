"""
Serviço de Auto-Complete de Processos Judiciais via DataJud (CNJ).

Responsabilidades:
    1. resolveTribunalEndpoint — detecta o alias do tribunal pelo número CNJ (NUPRO)
    2. Monta query ElasticSearch DSL por numeroProcesso.keyword
    3. Faz a requisição HTTP com autenticação ApiKey (reutiliza helper existente)
    4. Mapeia o JSON de retorno do DataJud para DTOs e modelo LegalAction
    5. Resolve partes do processo:
       - Busca por CPF/CNPJ exato (ClientService.get_by_document)
       - Fallback: fuzzy matching por nome (difflib — sem dependências extras)
    6. Faz upsert do processo (cria ou atualiza apenas campos modificados)
    7. Persiste partes e movimentos nas tabelas relacionadas

Reutilização explícita:
    - DataJudBatchService._post_json() → extraído para _post_json() neste módulo
    - DataJudBatchService._parse_date() → importado diretamente
    - tpu_mapping.classificar_area_juridica() → classificação da área jurídica
    - tpu_mapping.identificar_movimento_encerramento() → inferir status
    - tpu_mapping.extrair_movimentos_principais() → movimentos relevantes
    - ClientService.get_by_document() → busca de cliente por CPF/CNPJ
    - LegalActionService.get_by_number() → verifica se processo já existe
"""

import difflib
import json
import logging
import re
import urllib.error
import urllib.request
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.legal_action import LegalAction
from app.models.processo_movimento import ProcessoMovimento
from app.models.processo_parte import ProcessoParte
from app.schemas.datajud_autocomplete import (
    AssuntoDataJud,
    MovimentoDataJud,
    ParteEncontrada,
    ParteSugestao,
    ProcessoAutoCompleteResponse,
    ProcessoDadosDataJud,
)
from app.services.client_service import ClientService
from app.services.datajud_batch_service import DataJudBatchService
from app.services.legal_action_service import LegalActionService
from app.services.tpu_mapping import (
    classificar_area_juridica,
    extrair_movimentos_principais,
    identificar_movimento_encerramento,
)

logger = logging.getLogger(__name__)

# ──────────────────────────── Constantes ──────────────────────────────────

REQUEST_TIMEOUT_SECONDS = 30
FUZZY_MATCH_THRESHOLD = 0.80    # Score mínimo para fuzzy matching (0–1)
MAX_MOVIMENTOS_PERSISTIR = 50   # Máximo de movimentos a persistir por processo

# Mapeamento: (segmento J, código TT) → alias do endpoint DataJud
# Baseado em: https://datajud-wiki.cnj.jus.br/api-publica/endpoints
_TRIBUNAL_MAP: Dict[Tuple[str, str], str] = {}

# Justiça Estadual (J=1, TT=01..27 = estados)
_SIGLAS_TJ = {
    "01": "tjac", "02": "tjal", "03": "tjap", "04": "tjam", "05": "tjba",
    "06": "tjce", "07": "tjdf", "08": "tjes", "09": "tjgo", "10": "tjma",
    "11": "tjmt", "12": "tjms", "13": "tjmg", "14": "tjpa", "15": "tjpb",
    "16": "tjpr", "17": "tjpe", "18": "tjpi", "19": "tjrj", "20": "tjrn",
    "21": "tjrs", "22": "tjro", "23": "tjrr", "24": "tjsc", "25": "tjse",
    "26": "tjsp", "27": "tjto",
}
for _tt, _alias in _SIGLAS_TJ.items():
    _TRIBUNAL_MAP[("8", _tt)] = _alias
    _TRIBUNAL_MAP[("1", _tt)] = _alias

# Justiça Federal (J=4, TT=01..05 = TRFs)
_SIGLAS_TRF = {
    "01": "trf1", "02": "trf2", "03": "trf3", "04": "trf4", "05": "trf5",
}
for _tt, _alias in _SIGLAS_TRF.items():
    _TRIBUNAL_MAP[("4", _tt)] = _alias

# Justiça do Trabalho (J=5, TT=01..24 = TRTs)
for _i in range(1, 25):
    _tt = str(_i).zfill(2)
    _TRIBUNAL_MAP[("5", _tt)] = f"trt{_i}"

# Justiça Eleitoral (J=6)
_SIGLAS_TRE = {
    "01": "treac", "02": "treal", "03": "treap", "04": "tream", "05": "treba",
    "06": "trece", "07": "tredf", "08": "trees", "09": "trego", "10": "trema",
    "11": "tremt", "12": "trems", "13": "tremg", "14": "trepa", "15": "trepb",
    "16": "trepr", "17": "trepe", "18": "trepi", "19": "trerj", "20": "trern",
    "21": "trers", "22": "trero", "23": "trerr", "24": "tresc", "25": "tresp",
    "26": "trese", "27": "treto",
}
for _tt, _alias in _SIGLAS_TRE.items():
    _TRIBUNAL_MAP[("6", _tt)] = _alias

# Tribunais Superiores / Especiais
_TRIBUNAL_MAP[("2", "00")] = "stj"
_TRIBUNAL_MAP[("9", "00")] = "stf"
_TRIBUNAL_MAP[("8", "00")] = "stm"

# Justiça Militar Estadual (J=7)
_SIGLAS_TJM = {
    "13": "tjmmg", "21": "tjmrs", "26": "tjmsp",
}
for _tt, _alias in _SIGLAS_TJM.items():
    _TRIBUNAL_MAP[("7", _tt)] = _alias

DATAJUD_BASE = "https://api-publica.datajud.cnj.jus.br"


# ──────────────────────────── Service ─────────────────────────────────────


class DataJudAutoCompleteService:
    """
    Serviço de auto-complete de processos judiciais via DataJud.
    Todos os métodos são estáticos (padrão do projeto).
    """

    # ─── 1. Resolução de tribunal ──────────────────────────────────────────

    @staticmethod
    def resolve_tribunal_endpoint(numero_cnj: str) -> Tuple[str, str]:
        """
        Identifica o tribunal a partir do número CNJ e retorna a URL do endpoint DataJud.

        Formato CNJ: NNNNNNN-DD.AAAA.J.TT.OOOO
        - J  = segmento de justiça (1 char)
        - TT = código do tribunal  (2 chars)

        Returns:
            Tuple[url, alias] — URL do endpoint e alias do tribunal (ex: "tjsp")

        Raises:
            ValueError: se o número CNJ for inválido ou tribunal não suportado
        """
        # Normalizar: remover formatação, manter apenas dígitos
        limpo = re.sub(r"[^\d]", "", numero_cnj)
        if len(limpo) != 20:
            raise ValueError(
                f"Número CNJ inválido: '{numero_cnj}'. "
                "Esperado 20 dígitos no formato NNNNNNN-DD.AAAA.J.TT.OOOO"
            )

        # Posições: 0-6=processo, 7-8=dígitos, 9-12=ano, 13=J, 14-15=TT, 16-19=OOOO
        segmento_j = limpo[13]
        codigo_tt = limpo[14:16]

        alias = _TRIBUNAL_MAP.get((segmento_j, codigo_tt))

        # Fallback para STJ/STF com código TT variável
        if alias is None:
            if segmento_j == "2":
                alias = "stj"
            elif segmento_j == "9":
                alias = "stf"

        if alias is None:
            raise ValueError(
                f"Tribunal não suportado: J={segmento_j}, TT={codigo_tt}. "
                f"Número CNJ: '{numero_cnj}'"
            )

        url = f"{DATAJUD_BASE}/api_publica_{alias}/_search"
        logger.info(
            "Tribunal resolvido: numero_cnj=%s → alias=%s, url=%s",
            numero_cnj, alias, url,
        )
        return url, alias

    # ─── 2. Consulta principal ─────────────────────────────────────────────

    @staticmethod
    def buscar_por_numero(
        numero_cnj: str,
        organization_id: int,
        db: Session,
    ) -> ProcessoAutoCompleteResponse:
        """
        Busca um processo no DataJud pelo número CNJ e retorna os dados
        mapeados, com resolução de partes e verificação de existência local.

        Args:
            numero_cnj:       Número do processo no formato CNJ
            organization_id:  ID da organização do usuário autenticado
            db:               Sessão do banco de dados

        Returns:
            ProcessoAutoCompleteResponse com todos os dados mapeados

        Raises:
            ValueError:   Número CNJ inválido ou API Key não configurada
            RuntimeError: Erros de rede, HTTP ou parsing
        """
        api_key = settings.DATAJUD_API_KEY
        if not api_key:
            raise ValueError("DATAJUD_API_KEY não configurada no ambiente")

        # Normalizar número CNJ (remover espaços, garantir pontuação)
        numero_cnj = numero_cnj.strip()

        # Resolver tribunal
        url, alias = DataJudAutoCompleteService.resolve_tribunal_endpoint(numero_cnj)

        # Montar query DSL
        payload = DataJudAutoCompleteService._build_numero_query(numero_cnj)

        # Executar requisição (reutiliza helper do DataJudBatchService)
        try:
            response_data = DataJudBatchService._post_json(
                url=url, api_key=api_key, payload=payload
            )
        except RuntimeError as exc:
            msg = str(exc)
            # Tratar casos específicos de erro HTTP
            if "HTTP 401" in msg or "HTTP 403" in msg:
                raise RuntimeError(
                    "Autenticação inválida com o DataJud. Verifique a DATAJUD_API_KEY."
                ) from exc
            if "HTTP 429" in msg:
                raise RuntimeError(
                    "Limite de requisições do DataJud atingido. Tente novamente em instantes."
                ) from exc
            raise

        # Verificar hits
        hits = response_data.get("hits", {}).get("hits", [])
        if not hits:
            logger.info("Processo não encontrado no DataJud: %s", numero_cnj)
            return ProcessoAutoCompleteResponse(
                processo_encontrado=False,
                aviso="Processo não encontrado no DataJud para este número CNJ.",
            )

        source = hits[0].get("_source", {}) or {}

        # Verificar segredo de justiça
        if source.get("sigiloso") or source.get("segredoJustica"):
            logger.info("Processo sob segredo de justiça: %s", numero_cnj)
            return ProcessoAutoCompleteResponse(
                processo_encontrado=True,
                aviso="Este processo está sob segredo de justiça e não pode ser consultado.",
            )

        # Mapear dados do DataJud
        dados = DataJudAutoCompleteService._mapear_processo(source, alias)

        # Verificar se processo já existe localmente
        existing = LegalActionService.get_by_number(
            db, number=numero_cnj, organization_id=organization_id
        )
        processo_existente_id = existing.id if existing else None

        # Resolver partes
        partes_raw = DataJudAutoCompleteService._extrair_partes_raw(source)
        partes_encontradas, partes_nao_encontradas = DataJudAutoCompleteService._resolver_partes(
            partes_raw=partes_raw,
            organization_id=organization_id,
            db=db,
        )

        logger.info(
            "Auto-complete concluído: numero_cnj=%s, existente=%s, "
            "partes_encontradas=%d, partes_nao_encontradas=%d",
            numero_cnj,
            processo_existente_id,
            len(partes_encontradas),
            len(partes_nao_encontradas),
        )

        return ProcessoAutoCompleteResponse(
            processo_encontrado=True,
            processo_existente_id=processo_existente_id,
            dados=dados,
            partes_encontradas=partes_encontradas,
            partes_nao_encontradas=partes_nao_encontradas,
        )

    # ─── 3. Upsert do processo ─────────────────────────────────────────────

    @staticmethod
    def salvar_ou_atualizar(
        db: Session,
        legal_action: LegalAction,
        dados: ProcessoDadosDataJud,
        partes_encontradas: List[ParteEncontrada],
        partes_nao_encontradas: List[ParteSugestao],
        partes_confirmadas_criadas: Optional[List[Dict[str, Any]]] = None,
    ) -> LegalAction:
        """
        Atualiza um processo existente com os dados do DataJud.

        Regras:
        - Se datajud_preserve_manual=True, apenas campos DataJud (não editáveis
          manualmente, como partes e movimentos) são atualizados.
        - Se datajud_preserve_manual=False (padrão), todos os campos DataJud
          são sobrescritos, mas campos de negócio (título, descrição, status,
          usuários atribuídos) são preservados.
        - Partes e movimentos são sempre re-sincronizados.

        Args:
            legal_action:               Instância do processo a atualizar
            dados:                      Dados mapeados do DataJud
            partes_encontradas:         Partes com client_id resolvido
            partes_nao_encontradas:     Partes sem cliente cadastrado
            partes_confirmadas_criadas: Partes cujo cliente foi criado após confirmação
                                        [{nome, documento, polo, tipo_participacao, client_id}]
        """
        preserve = legal_action.datajud_preserve_manual

        # Campos DataJud — só atualiza se não preservar edições manuais
        if not preserve:
            if dados.tribunal:
                legal_action.tribunal = dados.tribunal
            if dados.court_name:
                legal_action.court_name = dados.court_name
            if dados.comarca:
                legal_action.comarca = dados.comarca
            if dados.vara:
                legal_action.vara = dados.vara
            if dados.orgao_julgador:
                legal_action.orgao_julgador = dados.orgao_julgador
            if dados.competencia:
                legal_action.competencia = dados.competencia
            if dados.magistrado:
                legal_action.magistrado = dados.magistrado
            if dados.classe_processual_codigo:
                legal_action.classe_processual_codigo = dados.classe_processual_codigo
            if dados.classe_processual_nome:
                legal_action.classe_processual_nome = dados.classe_processual_nome
            if dados.assuntos:
                legal_action.assuntos_json = json.dumps(
                    [a.model_dump() for a in dados.assuntos], ensure_ascii=False
                )
            if dados.data_ajuizamento:
                legal_action.filing_date = dados.data_ajuizamento
            if dados.data_distribuicao:
                legal_action.data_distribuicao = dados.data_distribuicao
            if dados.valor_causa is not None:
                legal_action.valor_causa = dados.valor_causa
            if dados.segredo_justica:
                legal_action.segredo_justica = dados.segredo_justica

        # Campos de sync — sempre atualizados independente de preserve_manual
        legal_action.datajud_synced_at = datetime.utcnow()
        if dados.datajud_last_update:
            legal_action.datajud_last_update = dados.datajud_last_update

        db.add(legal_action)

        # Re-sincronizar partes (sempre)
        db.query(ProcessoParte).filter(
            ProcessoParte.legal_action_id == legal_action.id
        ).delete()

        all_partes = list(partes_encontradas) + []
        confirmadas = partes_confirmadas_criadas or []

        # Partes encontradas → vinculadas a client_id
        for parte in partes_encontradas:
            db.add(ProcessoParte(
                legal_action_id=legal_action.id,
                polo=parte.polo,
                tipo_participacao=parte.tipo_participacao,
                nome=parte.nome,
                documento=parte.documento,
                oab=parte.oab,
                client_id=parte.client_id,
            ))

        # Partes não encontradas → sem client_id
        for parte in partes_nao_encontradas:
            # Verificar se foi confirmada/criada pelo usuário
            client_id_criado = None
            for conf in confirmadas:
                if conf.get("nome") == parte.nome or (
                    conf.get("documento") and conf.get("documento") == parte.documento
                ):
                    client_id_criado = conf.get("client_id")
                    break

            db.add(ProcessoParte(
                legal_action_id=legal_action.id,
                polo=parte.polo,
                tipo_participacao=parte.tipo_participacao,
                nome=parte.nome,
                documento=parte.documento,
                oab=parte.oab,
                client_id=client_id_criado,
            ))

        # Re-sincronizar movimentos (sempre, com limite)
        if dados.movimentos:
            db.query(ProcessoMovimento).filter(
                ProcessoMovimento.legal_action_id == legal_action.id
            ).delete()
            for mov in dados.movimentos[:MAX_MOVIMENTOS_PERSISTIR]:
                data_hora = None
                if mov.data_hora:
                    try:
                        normalized = mov.data_hora.replace("Z", "+00:00")
                        data_hora = datetime.fromisoformat(normalized)
                    except ValueError:
                        pass

                complemento_str = None
                if mov.complemento:
                    try:
                        complemento_str = json.dumps(mov.complemento, ensure_ascii=False)
                    except (TypeError, ValueError):
                        pass

                db.add(ProcessoMovimento(
                    legal_action_id=legal_action.id,
                    codigo=mov.codigo,
                    nome=mov.nome,
                    data_hora=data_hora,
                    complemento_json=complemento_str,
                ))

        db.commit()
        db.refresh(legal_action)
        return legal_action

    # ─── 4. Helpers de query ───────────────────────────────────────────────

    @staticmethod
    def _build_numero_query(numero_cnj: str) -> Dict[str, Any]:
        """
        Monta a query ElasticSearch DSL para busca por número de processo.
        Busca tanto a versão formatada quanto a versão contendo apenas os 20 dígitos.
        """
        limpo = re.sub(r"\D", "", numero_cnj)
        should_clauses = [
            {"term": {"numeroProcesso.keyword": numero_cnj}},
            {"term": {"numeroProcesso": numero_cnj}},
        ]
        if limpo:
            should_clauses.extend([
                {"term": {"numeroProcesso.keyword": limpo}},
                {"term": {"numeroProcesso": limpo}},
                {"match": {"numeroProcesso": limpo}},
            ])

        return {
            "size": 1,
            "query": {
                "bool": {
                    "should": should_clauses,
                    "minimum_should_match": 1,
                }
            },
            "_source": True,
        }

    # ─── 5. Mapeamento do JSON DataJud → DTO ──────────────────────────────

    @staticmethod
    def _mapear_processo(source: Dict[str, Any], alias: str) -> ProcessoDadosDataJud:
        """
        Mapeia todos os campos relevantes do _source do DataJud para o DTO.
        Não ignora campos úteis.
        """
        # Número do processo
        raw_num = (
            source.get("numeroProcesso")
            or source.get("numero_processo")
            or source.get("numeroProcessoCNJ")
            or ""
        )
        limpo_num = re.sub(r"\D", "", str(raw_num))
        if len(limpo_num) == 20:
            numero_cnj = f"{limpo_num[:7]}-{limpo_num[7:9]}.{limpo_num[9:13]}.{limpo_num[13]}.{limpo_num[14:16]}.{limpo_num[16:]}"
        else:
            numero_cnj = str(raw_num)

        # Classe processual
        classe_raw = source.get("classeProcessual") or {}
        if isinstance(classe_raw, str):
            classe_codigo, classe_nome = classe_raw, None
        else:
            classe_codigo = str(classe_raw.get("codigo") or "").strip() or None
            classe_nome = (classe_raw.get("nome") or "").strip() or None

        # Assuntos
        assuntos_raw = source.get("assuntos") or source.get("assunto") or []
        if not isinstance(assuntos_raw, list):
            assuntos_raw = [assuntos_raw]
        assuntos = [
            AssuntoDataJud(
                codigo=str(a.get("codigo") or "").strip() or None,
                nome=(a.get("nome") or "").strip() or None,
            )
            for a in assuntos_raw
            if isinstance(a, dict)
        ]

        # Órgão julgador
        orgao_raw = source.get("orgaoJulgador") or {}
        orgao_nome = None
        comarca = None
        vara = None
        competencia = None
        if isinstance(orgao_raw, dict):
            orgao_nome = (orgao_raw.get("nome") or "").strip() or None
            comarca = (orgao_raw.get("municipioNome") or "").strip() or None
            competencia = (orgao_raw.get("competencia") or "").strip() or None
            vara = (orgao_raw.get("vara") or orgao_raw.get("nomeOrgao") or "").strip() or None
        elif isinstance(orgao_raw, str):
            orgao_nome = orgao_raw.strip() or None

        # Magistrado
        magistrado = (source.get("magistrado") or "").strip() or None

        # Tribunal (nome completo)
        court_name = (source.get("tribunal") or source.get("nomeTribunal") or "").strip() or None

        # Datas
        data_ajuizamento = DataJudBatchService._parse_date(
            source.get("dataAjuizamento") or source.get("dataDistribuicao")
        )
        dist_raw = source.get("dataHoraDistribuicao") or source.get("dataDistribuicao")
        data_distribuicao = DataJudBatchService._parse_date(dist_raw)

        # Valor da causa
        valor_causa = None
        valor_raw = source.get("valorCausa") or source.get("valor_causa")
        if valor_raw is not None:
            try:
                valor_causa = Decimal(str(valor_raw))
            except (InvalidOperation, TypeError):
                pass

        # Segredo de justiça
        segredo = bool(source.get("sigiloso") or source.get("segredoJustica"))

        # Última atualização
        last_update = (
            source.get("dataHoraUltimaAtualizacao")
            or source.get("dataUltimaAtualizacao")
            or ""
        )
        last_update = str(last_update).strip() or None

        # Movimentos
        movimentos_raw = source.get("movimentos") or []
        movimentos_principais = extrair_movimentos_principais(movimentos_raw, max_movimentos=50)
        movimentos = [
            MovimentoDataJud(
                codigo=m.get("codigo") or None,
                nome=m.get("nome") or "",
                data_hora=str(m.get("data_hora") or "") or None,
                complemento=m.get("complemento"),
            )
            for m in movimentos_principais
            if m.get("nome")
        ]

        # Classificação da área jurídica (TPU)
        assunto_codigos = [a.codigo for a in assuntos if a.codigo]
        area_juridica = classificar_area_juridica(
            classe_codigo=classe_codigo,
            assunto_codigos=assunto_codigos,
        )

        return ProcessoDadosDataJud(
            numero_cnj=numero_cnj,
            tribunal=alias,
            classe_processual_codigo=classe_codigo,
            classe_processual_nome=classe_nome,
            assuntos=assuntos if assuntos else None,
            orgao_julgador=orgao_nome,
            comarca=comarca,
            vara=vara,
            competencia=competencia,
            magistrado=magistrado,
            court_name=court_name,
            data_ajuizamento=data_ajuizamento,
            data_distribuicao=data_distribuicao,
            valor_causa=valor_causa,
            segredo_justica=segredo,
            datajud_last_update=last_update,
            movimentos=movimentos if movimentos else None,
            area_juridica=area_juridica,
        )

    # ─── 6. Extração de partes raw do DataJud ─────────────────────────────

    @staticmethod
    def _extrair_partes_raw(source: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extrai a lista de partes do JSON do DataJud, normalizando a estrutura.
        O DataJud pode retornar partes em formatos ligeiramente diferentes.
        """
        partes = []

        # Formato 1: lista de polos com advogados aninhados
        polos = source.get("partes") or source.get("poloAtivo") or []
        if isinstance(polos, list):
            for polo_item in polos:
                if not isinstance(polo_item, dict):
                    continue
                # Determinar polo
                polo_label = (polo_item.get("polo") or "").lower()
                if "ativo" in polo_label:
                    polo_norm = "ativo"
                elif "passivo" in polo_label:
                    polo_norm = "passivo"
                else:
                    polo_norm = "terceiro"

                # Partes principais do polo
                for parte in polo_item.get("partes", []) or []:
                    if not isinstance(parte, dict):
                        continue
                    nome = (parte.get("nome") or "").strip()
                    if not nome:
                        continue
                    partes.append({
                        "nome": nome,
                        "documento": DataJudAutoCompleteService._normalizar_documento(
                            parte.get("cpf") or parte.get("cnpj") or parte.get("documento")
                        ),
                        "polo": polo_norm,
                        "tipo_participacao": "parte",
                        "oab": None,
                    })
                    # Advogados desta parte
                    for adv in parte.get("advogados", []) or []:
                        if not isinstance(adv, dict):
                            continue
                        nome_adv = (adv.get("nome") or "").strip()
                        if not nome_adv:
                            continue
                        partes.append({
                            "nome": nome_adv,
                            "documento": DataJudAutoCompleteService._normalizar_documento(
                                adv.get("cpf") or adv.get("documento")
                            ),
                            "polo": polo_norm,
                            "tipo_participacao": "advogado",
                            "oab": (adv.get("numeroOAB") or adv.get("oab") or "").strip() or None,
                        })

        # Formato 2: lista flat de partes
        partes_flat = source.get("representantes") or source.get("procuradores") or []
        if isinstance(partes_flat, list):
            for item in partes_flat:
                if not isinstance(item, dict):
                    continue
                nome = (item.get("nome") or "").strip()
                if not nome:
                    continue
                tipo = "procurador" if "procurador" in str(item).lower() else "representante"
                partes.append({
                    "nome": nome,
                    "documento": DataJudAutoCompleteService._normalizar_documento(
                        item.get("cpf") or item.get("cnpj") or item.get("documento")
                    ),
                    "polo": "terceiro",
                    "tipo_participacao": tipo,
                    "oab": None,
                })

        return partes

    # ─── 7. Resolução de partes ────────────────────────────────────────────

    @staticmethod
    def _resolver_partes(
        partes_raw: List[Dict[str, Any]],
        organization_id: int,
        db: Session,
    ) -> Tuple[List[ParteEncontrada], List[ParteSugestao]]:
        """
        Para cada parte do processo:
        1. Busca cliente por CPF/CNPJ exato (ClientService.get_by_document)
        2. Se não encontrar e houver nome, tenta fuzzy matching
        3. Separa em listas de encontradas / não encontradas

        Args:
            partes_raw:       Lista de partes extraídas do DataJud
            organization_id:  ID da organização para filtrar clientes
            db:               Sessão do banco

        Returns:
            Tuple[partes_encontradas, partes_nao_encontradas]
        """
        encontradas: List[ParteEncontrada] = []
        nao_encontradas: List[ParteSugestao] = []

        for parte in partes_raw:
            nome = parte.get("nome", "")
            documento = parte.get("documento")
            polo = parte.get("polo")
            tipo = parte.get("tipo_participacao")
            oab = parte.get("oab")

            client = None
            match_tipo = None
            match_score = None

            # 1. Busca por CPF/CNPJ exato
            if documento:
                client = ClientService.get_by_document(
                    db, document=documento, organization_id=organization_id
                )
                if client:
                    match_tipo = "documento"

            # 2. Fuzzy matching por nome (somente se sem documento ou não encontrado)
            if client is None and nome:
                client, match_score = DataJudAutoCompleteService._fuzzy_match_client(
                    nome=nome,
                    organization_id=organization_id,
                    db=db,
                )
                if client:
                    match_tipo = "nome_fuzzy"

            if client:
                encontradas.append(ParteEncontrada(
                    nome=nome,
                    documento=documento,
                    polo=polo,
                    tipo_participacao=tipo,
                    oab=oab,
                    client_id=client.id,
                    client_name=client.name,
                    match_tipo=match_tipo,
                    match_score=match_score,
                ))
            else:
                # Inferir tipo de cliente pelo tamanho do documento
                client_type = None
                if documento:
                    doc_digits = re.sub(r"\D", "", documento)
                    client_type = "business" if len(doc_digits) == 14 else "individual"

                nao_encontradas.append(ParteSugestao(
                    nome=nome,
                    documento=documento,
                    polo=polo,
                    tipo_participacao=tipo,
                    oab=oab,
                    client_type=client_type,
                ))

        return encontradas, nao_encontradas

    @staticmethod
    def _fuzzy_match_client(
        nome: str,
        organization_id: int,
        db: Session,
    ):
        """
        Tenta encontrar um cliente por similaridade de nome (difflib).
        Usa apenas a stdlib Python, sem dependências extras.

        Returns:
            Tuple[client | None, score | None]
        """
        from app.models.client import Client
        from sqlalchemy import func as sa_func

        # Buscar todos os clientes da organização (com limite razoável para performance)
        clientes = (
            db.query(Client)
            .filter(Client.organization_id == organization_id)
            .limit(1000)
            .all()
        )

        if not clientes:
            return None, None

        nome_lower = nome.lower()
        best_client = None
        best_score = 0.0

        for cli in clientes:
            score = difflib.SequenceMatcher(
                None, nome_lower, cli.name.lower()
            ).ratio()
            if score > best_score:
                best_score = score
                best_client = cli

        if best_score >= FUZZY_MATCH_THRESHOLD:
            logger.debug(
                "Fuzzy match: '%s' → '%s' (score=%.2f)",
                nome, best_client.name, best_score,
            )
            return best_client, round(best_score, 3)

        return None, None

    # ─── 8. Utilitários ───────────────────────────────────────────────────

    @staticmethod
    def _normalizar_documento(doc: Optional[Any]) -> Optional[str]:
        """Remove formatação de CPF/CNPJ, retorna apenas dígitos ou None."""
        if not doc:
            return None
        limpo = re.sub(r"\D", "", str(doc))
        return limpo if limpo else None
