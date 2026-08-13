"""
Schemas para o Auto-Complete de Processos Judiciais via DataJud (CNJ).

Fluxo:
  1. Frontend envia número CNJ → GET /integracao/datajud/autocomplete
  2. Backend consulta DataJud, resolve partes, retorna ProcessoAutoCompleteResponse
  3. Frontend pre-fill do formulário + modal de confirmação para partes não cadastradas
  4. Se usuário confirmar → frontend cria cliente via POST /clients e então POST /legal-actions
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


# ─────────────────────────────── Request ───────────────────────────────────


class DataJudAutoCompleteRequest(BaseModel):
    """Requisição de auto-complete por número CNJ."""
    numero_cnj: str = Field(
        ...,
        min_length=20,
        description="Número CNJ no formato NNNNNNN-DD.AAAA.J.TT.OOOO",
    )


# ────────────────────────────── Partes ─────────────────────────────────────


class ParteEncontrada(BaseModel):
    """
    Parte do processo que foi associada a um cliente já cadastrado na plataforma.
    O vínculo foi feito por CPF/CNPJ (exato) ou similaridade de nome (fuzzy).
    """
    nome: str
    documento: Optional[str] = None
    polo: Optional[str] = None              # 'ativo', 'passivo', 'terceiro'
    tipo_participacao: Optional[str] = None # 'parte', 'advogado', 'procurador', 'representante'
    oab: Optional[str] = None
    client_id: int                          # ID do cliente na base
    client_name: str                        # Nome do cliente na base
    match_tipo: str                         # 'documento' | 'nome_fuzzy'
    match_score: Optional[float] = None    # Score de similaridade (fuzzy only)

    model_config = ConfigDict(from_attributes=True)


class ParteSugestao(BaseModel):
    """
    Parte do processo que NÃO foi encontrada na base de clientes.
    O frontend exibirá um modal perguntando se o usuário deseja cadastrá-la.
    Os dados aqui são usados para pré-preencher o formulário de criação de cliente.
    """
    nome: str
    documento: Optional[str] = None         # CPF/CNPJ se disponível
    polo: Optional[str] = None
    tipo_participacao: Optional[str] = None
    oab: Optional[str] = None
    # Dados sugeridos para cadastro de cliente (pré-fill no modal)
    client_type: Optional[str] = None       # 'individual' | 'business' (inferido pelo tamanho do doc)
    model_config = ConfigDict(from_attributes=True)


# ─────────────────────── Dados extraídos do DataJud ────────────────────────


class AssuntoDataJud(BaseModel):
    """Assunto processual conforme TPU."""
    codigo: Optional[str] = None
    nome: Optional[str] = None


class MovimentoDataJud(BaseModel):
    """Movimentação do processo conforme TPU."""
    codigo: Optional[str] = None
    nome: str
    data_hora: Optional[str] = None
    complemento: Optional[Dict[str, Any]] = None


class ProcessoDadosDataJud(BaseModel):
    """
    Dados completos extraídos do DataJud para um processo.
    Todos os campos são opcionais (alguns processos podem omitir informações).
    """
    # Identificação
    numero_cnj: str
    tribunal: Optional[str] = None          # Alias do endpoint (ex: 'tjsp')

    # Classe e assuntos (TPU)
    classe_processual_codigo: Optional[str] = None
    classe_processual_nome: Optional[str] = None
    assuntos: Optional[List[AssuntoDataJud]] = None

    # Localização
    orgao_julgador: Optional[str] = None
    comarca: Optional[str] = None
    vara: Optional[str] = None
    competencia: Optional[str] = None
    magistrado: Optional[str] = None
    court_name: Optional[str] = None        # Nome completo do tribunal

    # Datas
    data_ajuizamento: Optional[date] = None
    data_distribuicao: Optional[date] = None

    # Financeiro
    valor_causa: Optional[Decimal] = None

    # Segredo de justiça
    segredo_justica: bool = False

    # Metadados de atualização do CNJ
    datajud_last_update: Optional[str] = None

    # Movimentos (lista dos mais relevantes extraídos)
    movimentos: Optional[List[MovimentoDataJud]] = None

    # Área jurídica classificada pela TPU (helper interno)
    area_juridica: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# ─────────────────────────────── Response ──────────────────────────────────


class ProcessoAutoCompleteResponse(BaseModel):
    """
    Resposta completa do auto-complete via DataJud.

    O frontend usa esta resposta para:
    1. Pre-fill do formulário de criação/edição de processo
    2. Exibir partes encontradas (clientes já cadastrados)
    3. Exibir modal de confirmação para partes não encontradas (sugestões de cadastro)
    """
    # Controle de fluxo
    processo_encontrado: bool = False       # Processo existe no DataJud
    processo_existente_id: Optional[int] = None  # ID local, se já cadastrado

    # Dados do processo
    dados: Optional[ProcessoDadosDataJud] = None

    # Partes
    partes_encontradas: List[ParteEncontrada] = Field(
        default_factory=list,
        description="Partes que possuem cliente cadastrado na plataforma",
    )
    partes_nao_encontradas: List[ParteSugestao] = Field(
        default_factory=list,
        description="Partes sem cliente cadastrado — frontend deve exibir modal de confirmação",
    )

    # Erros / avisos
    aviso: Optional[str] = None  # Ex: "Segredo de justiça", "Rate limit", etc.

    model_config = ConfigDict(from_attributes=True)
