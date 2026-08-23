"""
Serviço de Chat de Jurimetria.

Interpreta prompts de texto livre do usuário e:
1. Extrai número de processo (padrão CNJ) e tribunal via regex
2. Se houver número + tribunal → executa predição scikit-learn via DataJud
3. Se houver pergunta de estatísticas → consulta banco local
4. Caso contrário → orienta o usuário sobre o que pode perguntar
"""

import logging
import re
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

import numpy as np
from sqlalchemy.orm import Session

from app.models.jurimetria_dataset import JurimetriaDataset
from app.schemas.jurimetria_chat import JurimetriaChatRequest, JurimetriaChatResponse


# ─────────────────────────────────────────────────────────────────────────────
# Mapeamento de aliases de tribunais conhecidos
# ─────────────────────────────────────────────────────────────────────────────

TRIBUNAL_ALIASES: dict[str, str] = {
    # Tribunais de Justiça Estaduais
    "tjac": "tjac", "tjal": "tjal", "tjap": "tjap", "tjam": "tjam",
    "tjba": "tjba", "tjce": "tjce", "tjdf": "tjdft", "tjdft": "tjdft",
    "tjes": "tjes", "tjgo": "tjgo", "tjma": "tjma", "tjmt": "tjmt",
    "tjms": "tjms", "tjmg": "tjmg", "tjpa": "tjpa", "tjpb": "tjpb",
    "tjpr": "tjpr", "tjpe": "tjpe", "tjpi": "tjpi", "tjrj": "tjrj",
    "tjrn": "tjrn", "tjrs": "tjrs", "tjro": "tjro", "tjrr": "tjrr",
    "tjsc": "tjsc", "tjsp": "tjsp", "tjse": "tjse", "tjto": "tjto",
    # Tribunais Regionais do Trabalho
    "trt1": "trt1", "trt2": "trt2", "trt3": "trt3", "trt4": "trt4",
    "trt5": "trt5", "trt6": "trt6", "trt7": "trt7", "trt8": "trt8",
    "trt9": "trt9", "trt10": "trt10", "trt11": "trt11", "trt12": "trt12",
    "trt13": "trt13", "trt14": "trt14", "trt15": "trt15", "trt16": "trt16",
    "trt17": "trt17", "trt18": "trt18", "trt19": "trt19", "trt20": "trt20",
    "trt21": "trt21", "trt22": "trt22", "trt23": "trt23", "trt24": "trt24",
    # Tribunais Regionais Federais
    "trf1": "trf1", "trf2": "trf2", "trf3": "trf3",
    "trf4": "trf4", "trf5": "trf5", "trf6": "trf6",
    # Superiores
    "stj": "stj", "stf": "stf", "tst": "tst", "tse": "tse", "stm": "stm",
    # Militares
    "tjmmg": "tjmmg", "tjmrs": "tjmrs", "tjmsp": "tjmsp",
}

# Padrão CNJ: NNNNNNN-DD.AAAA.J.TT.OOOO ou 20 dígitos numéricos seguidos
CNJ_PATTERN_FORMATTED = re.compile(
    r"\b(\d{7}-\d{2}\.\d{4}\.\d{1}\.\d{2}\.\d{4})\b"
)
CNJ_PATTERN_UNFORMATTED = re.compile(
    r"\b(\d{20})\b"
)

# Palavras que indicam consulta de estatísticas
STAT_KEYWORDS = [
    "média", "media", "tempo médio", "tempo medio", "estatística",
    "estatistica", "percentil", "quantos dias", "demora", "demorando",
    "prazo médio", "prazo medio", "duração média", "duracao media",
    "duração", "duracao", "tramitação", "tramitacao",
]

# Palavras que indicam área jurídica
AREA_KEYWORDS: dict[str, list[str]] = {
    "Trabalhista": ["trabalhist", "trabalho", "clt", "trt", "empregad", "demissão", "demissao", "rescisão", "rescisao"],
    "Cível": ["cível", "civel", "civil", "indenização", "indenizacao", "contrato", "dano"],
    "Criminal": ["criminal", "penal", "crime", "réu", "reu", "preso", "detento", "tráfico", "trafico"],
    "Família": ["família", "familia", "divórcio", "divorcio", "guarda", "alimentos", "inventário", "inventario"],
    "Fazendária": ["fazend", "tributário", "tributario", "imposto", "fiscal", "fisco", "receita federal"],
}

# Mensagem de ajuda inicial
HELP_MESSAGE = (
    "Olá! Sou o assistente de jurimetria da Nomos, alimentado por um modelo "
    "de Machine Learning (scikit-learn).\n\n"
    "Posso te ajudar com a **Previsão de tempo de tramitação**.\n\n"
    "Para isso, informe o número do processo (padrão CNJ) e o tribunal. "
    "Ex: \"Quanto tempo falta para o processo 0001234-56.2022.8.26.0100 no TJSP?\"\n\n"
    "💡 **Para analisar um processo**, é só mandar o número no padrão CNJ e o tribunal (ex: *1001234-56.2023.8.26.0100 no TJSP*)."
)


class JurimetriaChatService:
    """
    Serviço de chat de jurimetria — interpreta prompts de texto livre
    e responde com predições ML ou estatísticas do banco.
    """

    # ─────────────────────────────────────────────────────────────────────────
    # Ponto de entrada principal
    # ─────────────────────────────────────────────────────────────────────────

    @staticmethod
    def processar(
        request: JurimetriaChatRequest,
        db: Session,
    ) -> JurimetriaChatResponse:
        mensagem = request.mensagem.strip()

        # 1. Tentar extrair número de processo e tribunal da mensagem atual
        numero_processo = JurimetriaChatService._extrair_numero_processo(mensagem)
        tribunal = JurimetriaChatService._extrair_tribunal(mensagem)

        # Se há um número de processo na mensagem atual, a prioridade é analisar ESTE processo
        if numero_processo:
            # Tentar resolver o tribunal automaticamente pelo número CNJ se não foi informado no texto
            if not tribunal:
                try:
                    from app.services.datajud_autocomplete_service import DataJudAutoCompleteService
                    _, tribunal_auto = DataJudAutoCompleteService.resolve_tribunal_endpoint(numero_processo)
                    tribunal = tribunal_auto
                except Exception:
                    pass

            return JurimetriaChatService._fluxo_predicao(
                mensagem=mensagem,
                numero_processo=numero_processo,
                tribunal=tribunal,
            )

        # 2. Se a mensagem atual não tem processo, verificar se é uma pergunta sobre estatísticas gerais
        if JurimetriaChatService._e_pergunta_estatistica(mensagem):
            tribunal_est = tribunal
            if not tribunal_est and request.historico:
                for item in reversed(request.historico):
                    if item.role == "user":
                        t = JurimetriaChatService._extrair_tribunal(item.content)
                        if t:
                            tribunal_est = t
                            break
            return JurimetriaChatService._fluxo_estatisticas(
                mensagem=mensagem,
                db=db,
                tribunal=tribunal_est,
            )

        # 3. Se o usuário enviou apenas o tribunal para um processo informado anteriormente sem tribunal
        if tribunal and request.historico:
            ultimo_assistant = next((m for m in reversed(request.historico) if m.role == "assistant"), None)
            estava_pedindo_tribunal = (
                ultimo_assistant and ("preciso saber em qual tribunal" in ultimo_assistant.content or "informe o tribunal" in ultimo_assistant.content)
            )

            if estava_pedindo_tribunal:
                numero_anterior = None
                for item in reversed(request.historico):
                    if item.role == "user":
                        n = JurimetriaChatService._extrair_numero_processo(item.content)
                        if n:
                            numero_anterior = n
                            break
                if numero_anterior:
                    return JurimetriaChatService._fluxo_predicao(
                        mensagem=mensagem,
                        numero_processo=numero_anterior,
                        tribunal=tribunal,
                    )

        # 4. Fallback: orientação para tentar outro processo ou tirar dúvidas
        if request.historico:
            ja_analisou_processo = any(
                JurimetriaChatService._extrair_numero_processo(item.content)
                for item in request.historico
                if item.role == "user"
            )

            if ja_analisou_processo:
                resposta_fallback = (
                    "💡 **Para analisar outro processo**, é só mandar o número no padrão CNJ e o tribunal.\n"
                    "Ex: *1001234-56.2023.8.26.0100 no TJSP*"
                )
            else:
                resposta_fallback = (
                    "Não entendi muito bem. Posso te ajudar com a previsão de tempo de tramitação.\n\n"
                    "💡 **Para analisar um processo**, é só mandar o número no padrão CNJ e o tribunal.\n"
                    "Ex: *1001234-56.2023.8.26.0100 no TJSP*"
                )

            return JurimetriaChatResponse(
                resposta=resposta_fallback,
                tipo="ajuda",
            )

        return JurimetriaChatResponse(
            resposta=HELP_MESSAGE,
            tipo="ajuda",
        )

    # ─────────────────────────────────────────────────────────────────────────
    # Extração de entidades
    # ─────────────────────────────────────────────────────────────────────────

    @staticmethod
    def _extrair_numero_processo(texto: str) -> Optional[str]:
        match = CNJ_PATTERN_FORMATTED.search(texto)
        if match:
            return match.group(1)
        match_raw = CNJ_PATTERN_UNFORMATTED.search(texto)
        if match_raw:
            digits = match_raw.group(1)
            return f"{digits[:7]}-{digits[7:9]}.{digits[9:13]}.{digits[13]}.{digits[14:16]}.{digits[16:]}"
        return None

    @staticmethod
    def _extrair_tribunal(texto: str) -> Optional[str]:
        texto_lower = texto.lower()
        for alias, codigo in TRIBUNAL_ALIASES.items():
            # Busca o alias como palavra completa (ex: "tjsp" mas não "atjsp")
            if re.search(rf"\b{re.escape(alias)}\b", texto_lower):
                return codigo
        return None

    @staticmethod
    def _extrair_area_juridica(texto: str) -> Optional[str]:
        texto_lower = texto.lower()
        for area, keywords in AREA_KEYWORDS.items():
            if any(kw in texto_lower for kw in keywords):
                return area
        return None

    @staticmethod
    def _e_pergunta_estatistica(texto: str) -> bool:
        texto_lower = texto.lower()
        return any(kw in texto_lower for kw in STAT_KEYWORDS)

    # ─────────────────────────────────────────────────────────────────────────
    # Fluxo 1: Predição ML com número de processo
    # ─────────────────────────────────────────────────────────────────────────

    @staticmethod
    def _fluxo_predicao(
        mensagem: str,
        numero_processo: str,
        tribunal: Optional[str],
    ) -> JurimetriaChatResponse:
        if not tribunal:
            return JurimetriaChatResponse(
                resposta=(
                    f"Encontrei o número do processo **{numero_processo}**, mas preciso saber "
                    "em qual tribunal ele tramita para fazer a predição.\n\n"
                    "Por favor, informe o tribunal. Ex: *TJSP*."
                ),
                tipo="texto",
                numero_processo=numero_processo,
            )

        # Lazy import para não carregar sklearn na inicialização
        try:
            from app.services.jurimetria_prediction_service import JurimetriaPredictionService
            resultado = JurimetriaPredictionService.predict(
                tribunal=tribunal,
                numero_processo=numero_processo,
            )
        except FileNotFoundError:
            return JurimetriaChatResponse(
                resposta=(
                    f"O processo **{numero_processo}** não foi encontrado no DataJud "
                    f"para o tribunal **{tribunal.upper()}**.\n\n"
                    "Verifique se o número do processo e o tribunal estão corretos."
                ),
                tipo="texto",
                numero_processo=numero_processo,
                tribunal=tribunal,
            )
        except RuntimeError as exc:
            mensagem_erro = str(exc)
            if "Modelo ativo" in mensagem_erro:
                return JurimetriaChatResponse(
                    resposta=(
                        "O modelo de predição ainda não foi treinado. "
                        "É necessário coletar dados de processos primeiro e executar o treinamento "
                        "antes de usar a previsão de tempo.\n\n"
                        "Enquanto isso, posso responder perguntas sobre estatísticas gerais dos "
                        "processos já registrados."
                    ),
                    tipo="texto",
                    numero_processo=numero_processo,
                    tribunal=tribunal,
                )
            return JurimetriaChatResponse(
                resposta=(
                    f"Ocorreu um erro ao consultar o DataJud: {mensagem_erro}\n\n"
                    "Tente novamente em alguns instantes."
                ),
                tipo="texto",
                numero_processo=numero_processo,
                tribunal=tribunal,
            )
        except ValueError as exc:
            return JurimetriaChatResponse(
                resposta=(
                    f"Não foi possível calcular a previsão para o processo **{numero_processo}**: {exc}"
                ),
                tipo="texto",
                numero_processo=numero_processo,
                tribunal=tribunal,
            )
        except Exception as exc:
            logger.exception(
                "Erro inesperado em _fluxo_predicao | processo=%s | tribunal=%s",
                numero_processo,
                tribunal,
            )
            return JurimetriaChatResponse(
                resposta=(
                    "Ocorreu um erro interno ao processar a predição. "
                    "Por favor, tente novamente."
                ),
                tipo="texto",
                numero_processo=numero_processo,
                tribunal=tribunal,
            )

        # Formatar resposta
        total = resultado.tempo_total_estimado_dias
        decorrido = resultado.tempo_decorrido_dias
        restante = resultado.tempo_estimado_restante_dias

        total_anos = total / 365
        partes = [
            f"Com base no modelo de jurimetria (RandomForest), analisei o processo "
            f"**{numero_processo}** no **{tribunal.upper()}**:\n"
        ]

        partes.append(
            f"📅 **Duração total estimada:** {total} dias "
            f"(aproximadamente {total_anos:.1f} ano{'s' if total_anos != 1 else ''})"
        )

        if decorrido is not None:
            decorrido_anos = decorrido / 365
            if getattr(resultado, "status", "em_andamento") == "finalizado":
                partes.append(
                    f"⌛ **Tempo decorrido (já finalizado):** {decorrido} dias "
                    f"(~{decorrido_anos:.1f} ano{'s' if round(decorrido_anos, 1) != 1.0 else ''})"
                )
            else:
                partes.append(
                    f"⏳ **Tempo já decorrido:** {decorrido} dias "
                    f"(~{decorrido_anos:.1f} ano{'s' if round(decorrido_anos, 1) != 1.0 else ''})"
                )

        if getattr(resultado, "status", "em_andamento") == "finalizado":
            partes.append("✅ **Este processo já foi finalizado!**")
        elif restante is not None:
            restante_anos = restante / 365
            if restante == 0:
                partes.append("✅ **O processo pode já estar próximo da conclusão** com base no tempo estimado.")
            else:
                partes.append(
                    f"🔮 **Tempo restante estimado:** {restante} dias "
                    f"(~{restante_anos:.1f} ano{'s' if round(restante_anos, 1) != 1.0 else ''})"
                )

        partes.append("\n_Previsão baseada em dados históricos do DataJud e modelo treinado com scikit-learn._")
        partes.append("\n💡 **Para tentar outro processo**, é só mandar o número no padrão CNJ e o tribunal (ex: *1001234-56.2023.8.26.0100 no TJSP*).")

        return JurimetriaChatResponse(
            resposta="\n".join(partes),
            tipo="predicao",
            numero_processo=numero_processo,
            tribunal=tribunal,
            tempo_total_estimado_dias=total,
            tempo_decorrido_dias=decorrido,
            tempo_estimado_restante_dias=restante,
        )

    # ─────────────────────────────────────────────────────────────────────────
    # Fluxo 2: Estatísticas do banco local
    # ─────────────────────────────────────────────────────────────────────────

    @staticmethod
    def _fluxo_estatisticas(
        mensagem: str,
        db: Session,
        tribunal: Optional[str],
    ) -> JurimetriaChatResponse:
        area = JurimetriaChatService._extrair_area_juridica(mensagem)

        query = db.query(JurimetriaDataset).filter(
            JurimetriaDataset.status_processo == "finalizado",
            JurimetriaDataset.duracao_dias.isnot(None),
        )

        if area:
            query = query.filter(JurimetriaDataset.area_juridica_principal == area)

        if tribunal:
            query = query.filter(JurimetriaDataset.tribunal == tribunal)

        registros = query.all()

        if not registros:
            contexto = []
            if area:
                contexto.append(f"área **{area}**")
            if tribunal:
                contexto.append(f"tribunal **{tribunal.upper()}**")
            filtro_str = " e ".join(contexto) if contexto else "os critérios informados"

            return JurimetriaChatResponse(
                resposta=(
                    f"Não encontrei processos finalizados para {filtro_str} no banco de dados.\n\n"
                    "Você pode coletar dados via **Integração DataJud** para enriquecer as estatísticas."
                ),
                tipo="estatistica",
            )

        duracoes = [r.duracao_dias for r in registros]
        arr = np.array(duracoes)

        media = float(np.mean(arr))
        mediana = float(np.median(arr))
        p25 = float(np.percentile(arr, 25))
        p75 = float(np.percentile(arr, 75))
        p90 = float(np.percentile(arr, 90))
        minimo = int(np.min(arr))
        maximo = int(np.max(arr))
        total_processos = len(registros)

        # Montar cabeçalho
        cabecalho_partes = []
        if area:
            cabecalho_partes.append(f"área **{area}**")
        if tribunal:
            cabecalho_partes.append(f"tribunal **{tribunal.upper()}**")
        cabecalho = (
            "Estatísticas de processos finalizados"
            + (f" — {' e '.join(cabecalho_partes)}" if cabecalho_partes else "")
            + f" ({total_processos} processos analisados):\n"
        )

        linhas = [
            cabecalho,
            f"📊 **Tempo médio:** {media:.0f} dias (~{media/365:.1f} anos)",
            f"📊 **Mediana:** {mediana:.0f} dias (~{mediana/365:.1f} anos)",
            f"📊 **Percentil 25%:** {p25:.0f} dias — 25% dos processos concluem antes disso",
            f"📊 **Percentil 75%:** {p75:.0f} dias — 75% dos processos concluem antes disso",
            f"📊 **Percentil 90%:** {p90:.0f} dias — apenas 10% demoram mais",
            f"📊 **Mínimo:** {minimo} dias | **Máximo:** {maximo} dias",
            "\n_Dados baseados nos processos finalizados registrados no banco local._",
        ]

        return JurimetriaChatResponse(
            resposta="\n".join(linhas),
            tipo="estatistica",
            tribunal=tribunal,
        )
