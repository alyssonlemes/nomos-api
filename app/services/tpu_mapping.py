"""
Mapeamento da Tabela Processual Unificada (TPU) do CNJ.

Conforme Seção 2 do Master Prompt:
- Classes: https://www.cnj.jus.br/sgt/consulta_publica_classes.php
- Assuntos: https://www.cnj.jus.br/sgt/consulta_publica_assuntos.php

Este módulo traduz termos de área jurídica (ex: "Criminal") para os
códigos TPU correspondentes, permitindo filtragem precisa na API DataJud.

Também contém os termos de encerramento (Seção 3.2 do MD) para inferir
a data de fim dos processos a partir do array de movimentos.
"""

from typing import Dict, List, Optional, Set


# ─────────────────────── Classificação por Área Jurídica ──────────────────────
# Mapeamento: área → lista de códigos de classe processual (TPU)
# Fonte: Tabela Processual Unificada do CNJ

AREAS_CLASSES: Dict[str, List[str]] = {
    "Criminal": [
        "268",   # Ação Penal - Procedimento Ordinário
        "269",   # Ação Penal - Procedimento Sumário (Processo Criminal)
        "270",   # Ação Penal - Procedimento Sumaríssimo
        "271",   # Ação Penal de Competência do Júri
        "272",   # Ação Penal Militar
        "274",   # Queixa-Crime
        "279",   # Inquérito Policial
        "280",   # Execução Penal
        "281",   # Auto de Prisão em Flagrante
        "282",   # Habeas Corpus Criminal
        "283",   # Ação Penal - Procedimento Ordinário (2ª instância)
        "355",   # Carta Precatória Criminal
        "417",   # Apelação Criminal
        "1707",  # Ação Penal - Procedimento Especial
        "1708",  # Ação Penal - Procedimento Especial de Leis Esparsas
    ],
    "Família": [
        "22",    # Divórcio Consensual
        "23",    # Divórcio Litigioso
        "25",    # Separação Consensual
        "26",    # Separação Litigiosa
        "27",    # Reconhecimento / Dissolução de União Estável
        "28",    # Alimentos
        "29",    # Investigação de Paternidade
        "30",    # Guarda
        "36",    # Regulamentação de Visitas
        "37",    # Tutela
        "38",    # Curatela
        "39",    # Interdição
        "49",    # Partilha
        "175",   # Inventário
        "176",   # Arrolamento
        "12372", # Divórcio Consensual (código atualizado)
        "12373", # Divórcio Litigioso (código atualizado)
    ],
    "Cível": [
        "7",     # Procedimento Comum Cível
        "12",    # Procedimento Sumário
        "14",    # Cumprimento de Sentença
        "40",    # Monitória
        "47",    # Ação Rescisória
        "63",    # Execução de Título Extrajudicial
        "64",    # Execução de Título Judicial
        "65",    # Ação Monitória
        "67",    # Mandado de Segurança Cível
        "69",    # Habeas Data
        "85",    # Ação Civil Pública
        "100",   # Embargos à Execução
        "114",   # Impugnação de Crédito
        "131",   # Procedimento do Juizado Especial Cível
        "159",   # Busca e Apreensão em Alienação Fiduciária
        "165",   # Despejo
        "167",   # Renovatória de Locação
        "170",   # Usucapião
        "173",   # Reintegração / Manutenção de Posse
        "178",   # Consignação em Pagamento
        "185",   # Ação Rescisória (1ª instância)
        "186",   # Indenização por Dano Moral
        "187",   # Indenização por Dano Material
        "198",   # Apelação Cível
        "202",   # Agravo de Instrumento
        "206",   # Cobrança
        "229",   # Exibição de Documentos ou Coisa
        "233",   # Cautelar de Produção Antecipada de Provas
        "301",   # Ação de Obrigação de Fazer
        "319",   # Ação de Despejo por Falta de Pagamento
        "12078", # Cumprimento de Sentença contra a Fazenda Pública
        "12154", # Execução de Título Extrajudicial (código atualizado)
    ],
    "Trabalhista": [
        "985",   # Dissídio Individual
        "986",   # Dissídio Coletivo
        "987",   # Ação Trabalhista - Rito Ordinário
        "988",   # Ação Trabalhista - Rito Sumaríssimo
        "989",   # Ação Trabalhista - Rito Sumário
        "990",   # Execução de Título Extrajudicial Trabalhista
        "991",   # Execução de Título Judicial Trabalhista
        "992",   # Mandado de Segurança Trabalhista
        "993",   # Habeas Corpus Trabalhista
        "994",   # Ação de Consignação em Pagamento Trabalhista
        "995",   # Ação Rescisória Trabalhista
        "996",   # Inquérito para Apuração de Falta Grave
        "1009",  # Reclamação Trabalhista
    ],
    "Militar": [
        "272",   # Ação Penal Militar
        "1721",  # Conselho Permanente de Justiça
        "1722",  # Conselho Especial de Justiça
        "1723",  # Deserção
        "1724",  # Instrução Provisória de Deserção
        "1725",  # Habeas Corpus Militar
    ],
    "Tributário": [
        "60",    # Execução Fiscal
        "90",    # Ação Anulatória de Débito Fiscal
        "97",    # Mandado de Segurança contra Exação Fiscal
        "156",   # Embargos à Execução Fiscal
        "448",   # Ação Declaratória de Inexistência de Débito Fiscal
        "1116",  # Execução Fiscal (código atualizado)
    ],
    "Consumidor": [
        "131",   # Procedimento do Juizado Especial Cível
        "7",     # Procedimento Comum Cível
        "85",    # Ação Civil Pública
        "186",   # Indenização por Dano Moral
        "187",   # Indenização por Dano Material
    ],
    "Administrativo": [
        "67",    # Mandado de Segurança Cível
        "69",    # Habeas Data
        "85",    # Ação Civil Pública
        "105",   # Ação Popular
        "120",   # Ação de Improbidade Administrativa
    ],
}

# ─────────────── Mapeamento por Assuntos (TPU - Ramos do Direito) ─────────────
# Códigos de nível superior dos ramos do Direito conforme TPU

AREAS_ASSUNTOS: Dict[str, List[str]] = {
    "Criminal": [
        "287",    # DIREITO PENAL
        "288",    # DIREITO PROCESSUAL PENAL
        "3603",   # DIREITO PENAL MILITAR
        "5826",   # Crimes contra a Pessoa
        "5827",   # Crimes contra o Patrimônio
        "5828",   # Crimes contra a Dignidade Sexual
        "3377",   # Crimes de Trânsito
        "3536",   # Crimes contra a Administração Pública
        "3540",   # Crimes contra a Fé Pública
        "3578",   # Tráfico de Drogas
        "3591",   # Crimes contra o Meio Ambiente
        "5556",   # Crimes do Estatuto do Desarmamento
        "7688",   # Violência Doméstica
        "9985",   # Lei Maria da Penha
    ],
    "Família": [
        "5626",   # Família (DIREITO CIVIL)
        "6105",   # Casamento
        "6106",   # Divórcio
        "6067",   # Alimentos
        "6091",   # Guarda
        "9037",   # União Estável
        "6095",   # Regulamentação de Visitas
        "6112",   # Adoção
        "6071",   # Filiação
        "7673",   # Alienação Parental
        "6099",   # Tutela e Curatela
    ],
    "Cível": [
        "899",    # DIREITO CIVIL
        "864",    # DIREITO DO CONSUMIDOR
        "7947",   # Obrigações
        "7681",   # Contratos
        "8826",   # Direitos Reais
        "7771",   # Responsabilidade Civil
        "10432",  # Locação de Imóvel
        "10216",  # Compra e Venda
        "10218",  # Prestação de Serviços
        "10445",  # Seguro
        "6226",   # Condomínio
        "10451",  # Enriquecimento sem Causa
    ],
    "Trabalhista": [
        "1156",   # DIREITO DO TRABALHO
        "2027",   # DIREITO PROCESSUAL DO TRABALHO
        "1654",   # Rescisão do Contrato de Trabalho
        "1655",   # FGTS
        "1656",   # Salário e Remuneração
        "1657",   # Férias
        "1658",   # 13º Salário
        "1659",   # Horas Extras
        "1663",   # Acidente de Trabalho
        "1691",   # Dano Moral Trabalhista
    ],
    "Militar": [
        "3603",   # DIREITO PENAL MILITAR
        "3604",   # DIREITO PROCESSUAL PENAL MILITAR
        "10943",  # Administração Militar
        "10113",  # Deserção
    ],
    "Tributário": [
        "6144",   # DIREITO TRIBUTÁRIO
        "6152",   # Impostos
        "6160",   # Taxas
        "10326",  # Contribuições
        "10434",  # Execução Fiscal / Dívida Ativa
        "6145",   # Crédito Tributário
    ],
    "Administrativo": [
        "10110",  # DIREITO ADMINISTRATIVO E OUTRAS MATÉRIAS DE DIREITO PÚBLICO
        "9985",   # Servidor Público Civil
        "10028",  # Licitações e Contratos Administrativos
        "10060",  # Improbidade Administrativa
        "10095",  # Desapropriação
        "10070",  # Poder de Polícia
    ],
}

# ──────────────────── Termos de Encerramento (Seção 3.2 do MD) ────────────────
# Termos que indicam encerramento definitivo de um processo.
# Usados para busca no array `movimentos` da API DataJud.

TERMOS_ENCERRAMENTO: List[str] = [
    "Baixa Definitiva",
    "Arquivamento",
    "Arquivamento Definitivo",
    "Trânsito em Julgado",
    "Extinção do Processo",
    "Julgado Extinto",
    "Extinção",
    "Processo Extinto",
    "Sentença Transitada em Julgado",
    "Encerramento",
    "Cancelamento",
    "Distribuição Cancelada",
    "Remessa ao Arquivo",
    "Baixa na Distribuição",
    "Cumprimento de Sentença Encerrado",
    "Execução Extinta",
]

# Códigos de movimento de encerramento (TPU movimentação)
# ATENÇÃO: NÃO incluir códigos que não são encerramentos reais.
# 11010 = "Mero expediente" (ato ordinário, NÃO é encerramento)
# 246 = "Desarquivamento" (reabertura, NÃO é encerramento)
CODIGOS_ENCERRAMENTO: Set[str] = {
    "22",    # Baixa Definitiva
    "196",   # Extinção da execução ou do cumprimento da sentença
    "245",   # Arquivamento Definitivo
    "848",   # Trânsito em Julgado
    "861",   # Extinção do Processo
    "893",   # Remessa ao Arquivo
    "946",   # Arquivamento por Acordo ou Desistência
    "1063",  # Determinação de arquivamento de procedimentos investigatórios
    "10964", # Baixa na Distribuição
}

# ─────────────── Termos normalizados para busca case-insensitive ──────────────

TERMOS_ENCERRAMENTO_LOWER: List[str] = [t.lower() for t in TERMOS_ENCERRAMENTO]


def classificar_area_juridica(
    classe_codigo: Optional[str] = None,
    assunto_codigos: Optional[List[str]] = None,
) -> Optional[str]:
    """
    Classifica a área jurídica principal a partir dos códigos TPU.

    Primeiro tenta classificar pela classe processual (mais precisa).
    Se não encontrar, tenta pelos assuntos.

    Args:
        classe_codigo: código da classe processual principal
        assunto_codigos: lista de códigos de assuntos

    Returns:
        Nome da área jurídica ("Criminal", "Família", etc.) ou None
    """
    # 1. Tentar por classe processual
    if classe_codigo:
        for area, codigos in AREAS_CLASSES.items():
            if str(classe_codigo) in codigos:
                return area

    # 2. Tentar por assuntos
    if assunto_codigos:
        area_scores: Dict[str, int] = {}
        for cod in assunto_codigos:
            for area, codigos in AREAS_ASSUNTOS.items():
                if str(cod) in codigos:
                    area_scores[area] = area_scores.get(area, 0) + 1

        if area_scores:
            return max(area_scores, key=area_scores.get)

    return None


def obter_codigos_por_area(area: str) -> Dict[str, List[str]]:
    """
    Retorna os códigos de classe e assunto para uma área jurídica.

    Args:
        area: nome da área (ex: "Criminal")

    Returns:
        dict com "classes" e "assuntos"
    """
    return {
        "classes": AREAS_CLASSES.get(area, []),
        "assuntos": AREAS_ASSUNTOS.get(area, []),
    }


def listar_areas_disponiveis() -> List[Dict[str, object]]:
    """
    Lista todas as áreas jurídicas disponíveis com seus códigos.

    Returns:
        Lista de dicts com nome, total de classes e total de assuntos
    """
    areas = []
    all_area_names = set(list(AREAS_CLASSES.keys()) + list(AREAS_ASSUNTOS.keys()))

    for area_name in sorted(all_area_names):
        areas.append({
            "nome": area_name,
            "total_classes": len(AREAS_CLASSES.get(area_name, [])),
            "total_assuntos": len(AREAS_ASSUNTOS.get(area_name, [])),
            "codigos_classes": AREAS_CLASSES.get(area_name, []),
            "codigos_assuntos": AREAS_ASSUNTOS.get(area_name, []),
        })

    return areas


def identificar_movimento_encerramento(
    movimentos: List[Dict],
) -> Optional[Dict]:
    """
    Identifica o movimento de encerramento mais recente de um processo.

    Conforme Seção 3.2 do MD:
    - Itera sobre o array movimentos
    - Procura por movimentos com nome contendo termos de encerramento
    - Retorna o mais recente

    Args:
        movimentos: lista de movimentos do processo (da API DataJud)

    Returns:
        Dict com "nome", "dataHora" e "codigo" do movimento de encerramento,
        ou None se o processo está em andamento.
    """
    if not movimentos:
        return None

    encerramento_encontrado = None
    data_mais_recente = None

    for mov in movimentos:
        nome = (mov.get("nome") or mov.get("descricao") or "").strip()
        codigo = str(mov.get("codigo") or mov.get("codigoNacional") or "")
        data_hora = mov.get("dataHora") or mov.get("data") or mov.get("dataMovimento")

        # Verificar por nome (case-insensitive, substring match)
        nome_lower = nome.lower()
        is_encerramento = any(
            termo in nome_lower for termo in TERMOS_ENCERRAMENTO_LOWER
        )

        # Verificar por código
        if not is_encerramento and codigo in CODIGOS_ENCERRAMENTO:
            is_encerramento = True

        if is_encerramento:
            # Manter o mais recente
            if data_mais_recente is None or (data_hora and str(data_hora) > str(data_mais_recente)):
                data_mais_recente = data_hora
                encerramento_encontrado = {
                    "nome": nome,
                    "dataHora": data_hora,
                    "codigo": codigo,
                }

    return encerramento_encontrado


def extrair_movimentos_principais(
    movimentos: List[Dict],
    max_movimentos: int = 10,
) -> List[Dict]:
    """
    Extrai uma lista simplificada dos movimentos mais relevantes.

    Args:
        movimentos: lista completa de movimentos
        max_movimentos: número máximo de movimentos a retornar

    Returns:
        Lista simplificada de movimentos
    """
    if not movimentos:
        return []

    # Priorizar movimentos com códigos conhecidos ou nomes relevantes
    resultado = []
    for mov in movimentos:
        nome = (mov.get("nome") or mov.get("descricao") or "").strip()
        if not nome:
            continue

        resultado.append({
            "nome": nome,
            "data_hora": mov.get("dataHora") or mov.get("data") or mov.get("dataMovimento"),
            "codigo": str(mov.get("codigo") or mov.get("codigoNacional") or ""),
        })

    # Ordenar por data (mais recente primeiro) e limitar
    resultado.sort(key=lambda x: x.get("data_hora") or "", reverse=True)
    return resultado[:max_movimentos]
