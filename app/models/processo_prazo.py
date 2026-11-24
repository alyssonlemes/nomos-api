from sqlalchemy import Column, Date, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base

class ProcessoPrazo(Base):
    """Prazo derivado de uma movimentação ou publicação recebida por webhook."""

    __tablename__ = "processo_prazos"
    __table_args__ = (
        UniqueConstraint(
            "legal_action_id",
            "escavador_movimentacao_id",
            name="uq_processo_prazo_movimentacao",
        ),
        Index("idx_processo_prazo_org_status", "organization_id", "status"),
        Index("idx_processo_prazo_acao", "legal_action_id", "status"),
    )

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    legal_action_id = Column(Integer, ForeignKey("legal_actions.id", ondelete="CASCADE"), nullable=False)
    escavador_movimentacao_id = Column(String, nullable=False)
    origem = Column(String(32), nullable=False)
    conteudo = Column(Text, nullable=False)
    data_movimentacao = Column(Date, nullable=True)
    dias_prazo = Column(Integer, nullable=True)
    data_vencimento = Column(Date, nullable=True)
    status = Column(String(16), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    legal_action = relationship("LegalAction", backref="prazos")
