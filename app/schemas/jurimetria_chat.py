from typing import List, Optional

from pydantic import BaseModel, Field


class ChatHistoricoItem(BaseModel):
    """
    Um item do histórico de conversa (role + conteúdo).
    """
    role: str = Field(..., description="'user' ou 'assistant'")
    content: str = Field(..., description="Texto da mensagem")


class JurimetriaChatRequest(BaseModel):
    """
    Requisição do chat de jurimetria com texto livre.
    """
    mensagem: str = Field(..., min_length=1, max_length=2000, description="Pergunta ou comando em linguagem natural")
    historico: List[ChatHistoricoItem] = Field(
        default_factory=list,
        description="Histórico das mensagens anteriores da conversa (excluindo a mensagem atual)",
    )


class JurimetriaChatResponse(BaseModel):
    """
    Resposta do assistente de jurimetria.
    """
    resposta: str
    tipo: str = "texto"  # "texto" | "predicao" | "estatistica" | "ajuda"
    numero_processo: Optional[str] = None
    tribunal: Optional[str] = None
    tempo_total_estimado_dias: Optional[int] = None
    tempo_decorrido_dias: Optional[int] = None
    tempo_estimado_restante_dias: Optional[int] = None

