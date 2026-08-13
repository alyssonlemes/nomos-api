from sqlalchemy import Column, Integer, String, ForeignKey, Index
from sqlalchemy.orm import relationship

from app.database import Base


class ProcessoParte(Base):
    """
    Partes de um processo judicial obtidas via DataJud.

    Relacionamento 1:N com LegalAction (um processo possui múltiplas partes).

    polo:
        'ativo'    → autor / requerente
        'passivo'  → réu / requerido
        'terceiro' → interveniente / amicus curiae

    tipo_participacao:
        'parte'          → autor, réu, etc.
        'advogado'       → advogado constituído
        'procurador'     → procurador (ex: MP, AGU)
        'representante'  → representante legal
    """
    __tablename__ = "processo_partes"
    __table_args__ = (
        Index("idx_processo_partes_legal_action", "legal_action_id"),
        Index("idx_processo_partes_documento", "documento"),
        Index("idx_processo_partes_client", "client_id"),
    )

    id = Column(Integer, primary_key=True, index=True)

    # Processo vinculado
    legal_action_id = Column(
        Integer,
        ForeignKey("legal_actions.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Polo processual e tipo de participação
    polo = Column(String(20))              # 'ativo', 'passivo', 'terceiro'
    tipo_participacao = Column(String(30)) # 'parte', 'advogado', 'procurador', 'representante'

    # Dados da parte
    nome = Column(String, nullable=False)
    documento = Column(String, index=True)     # CPF / CNPJ (sem máscara)
    oab = Column(String)                       # Número OAB (apenas para advogados)

    # Vínculo com cliente cadastrado na plataforma (resolvido no auto-complete)
    client_id = Column(
        Integer,
        ForeignKey("clients.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships
    legal_action = relationship("LegalAction", back_populates="partes")
    client = relationship("Client", foreign_keys=[client_id])

    def __repr__(self):
        return (
            f"<ProcessoParte(id={self.id}, "
            f"nome='{self.nome}', "
            f"polo='{self.polo}', "
            f"tipo='{self.tipo_participacao}')>"
        )
