from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum, ForeignKey, Text, Date, Index, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

from app.database import Base


class LegalStatus(str, enum.Enum):
    """Status jurídico do processo"""
    PRE_TRIAL = "pre_trial"          # Pré-processual
    FILING = "filing"                # Ajuizamento
    LITIGATION = "litigation"        # Contencioso
    EXECUTION = "execution"          # Execução
    APPEAL = "appeal"                # Recurso
    FINALIZED = "finalized"          # Finalizado
    ARCHIVED = "archived"            # Arquivado


class LegalAction(Base):
    """
    Modelo de Ação Jurídica / Processo
    """
    __tablename__ = "legal_actions"
    __table_args__ = (
        UniqueConstraint('organization_id', 'number', name='uq_legal_actions_org_number'),
        Index('idx_legal_action_org_status', 'organization_id', 'legal_status'),
        Index('idx_legal_action_client', 'client_id'),
        Index('idx_legal_action_org_client', 'organization_id', 'client_id'),
    )

    id = Column(Integer, primary_key=True, index=True)
    
    # Informações básicas
    number = Column(String, index=True, nullable=False)  # Número do processo
    title = Column(String, nullable=False, index=True)
    description = Column(Text)
    
    # Relacionamentos
    client_id = Column(Integer, ForeignKey("clients.id", ondelete="CASCADE"), nullable=False)
    client = relationship("Client", backref="legal_actions")
    
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    user = relationship("User", backref="legal_actions")
    
    # Organização
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    organization = relationship("Organization", backref="legal_actions")
    
    # Tipo e status
    action_type_id = Column(Integer, ForeignKey("legal_action_types.id", ondelete="RESTRICT"), nullable=False)
    action_type = relationship("LegalActionType", back_populates="legal_actions")
    legal_status = Column(Enum(LegalStatus), default=LegalStatus.PRE_TRIAL, nullable=False)
    
    # Tribunal (opcional)
    court_name = Column(String)
    
    # Datas
    filing_date = Column(Date)
    closing_date = Column(Date)
    
    # Metadados
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<LegalAction(id={self.id}, number='{self.number}', title='{self.title}', organization_id={self.organization_id})>"
