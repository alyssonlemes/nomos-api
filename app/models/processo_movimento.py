from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Text, Index
from sqlalchemy.orm import relationship

from app.database import Base


class ProcessoMovimento(Base):
    """
    Movimentações de um processo judicial obtidas via DataJud.

    Relacionamento 1:N com LegalAction (um processo possui múltiplos movimentos).
    Os movimentos são ordenados cronologicamente por data_hora (decrescente = mais recente primeiro).
    """
    __tablename__ = "processo_movimentos"
    __table_args__ = (
        Index("idx_processo_movimentos_legal_action", "legal_action_id"),
        Index("idx_processo_movimentos_data", "legal_action_id", "data_hora"),
        Index("idx_processo_movimentos_codigo", "codigo"),
    )

    id = Column(Integer, primary_key=True, index=True)

    # Processo vinculado
    legal_action_id = Column(
        Integer,
        ForeignKey("legal_actions.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Dados do movimento (conforme TPU de movimentações do CNJ)
    codigo = Column(String, index=True)         # Código TPU do movimento
    nome = Column(String, nullable=False)       # Nome/descrição do movimento
    data_hora = Column(DateTime(timezone=True)) # dataHora do movimento

    # Complemento (JSON serializado com campos adicionais retornados pelo DataJud)
    complemento_json = Column(Text)

    # Relationship
    legal_action = relationship("LegalAction", back_populates="movimentos")

    def __repr__(self):
        return (
            f"<ProcessoMovimento(id={self.id}, "
            f"codigo='{self.codigo}', "
            f"nome='{self.nome}', "
            f"data_hora={self.data_hora})>"
        )
