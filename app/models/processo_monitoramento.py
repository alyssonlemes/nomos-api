from sqlalchemy import BigInteger, Boolean, Column, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base

class ProcessoMonitoramento(Base):
    """Acompanhamento de um processo na Juri+, limitado por escritório.

    escavador_id guarda o id do monitoramento na Juri+. O nome da coluna ficou
    do provedor anterior para não reescrever a tabela.
    """

    __tablename__ = "processo_monitoramentos"
    __table_args__ = (
        UniqueConstraint("legal_action_id", name="uq_processo_monitoramento_acao"),
        Index("idx_processo_monitoramento_org_ativo", "organization_id", "ativo", "status"),
        Index("idx_processo_monitoramento_escavador", "escavador_id"),
        Index("idx_processo_monitoramento_digitos", "numero_digitos"),
    )

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    legal_action_id = Column(Integer, ForeignKey("legal_actions.id", ondelete="CASCADE"), nullable=False)
    escavador_id = Column(BigInteger, nullable=True)
    numero_cnj = Column(String, nullable=False)
    numero_digitos = Column(String(20), nullable=False)
    status = Column(String(32), nullable=False, default="PENDENTE")
    frequencia = Column(String(16), nullable=False, default="DIARIA")
    ativo = Column(Boolean, nullable=False, default=True)
    data_ultima_verificacao = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    legal_action = relationship("LegalAction", backref="monitoramento")
