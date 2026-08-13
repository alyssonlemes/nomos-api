from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, Date, Index, UniqueConstraint, Numeric
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

from app.database import Base


class LegalAction(Base):
    """
    Modelo de Ação Jurídica / Processo
    """
    __tablename__ = "legal_actions"
    __table_args__ = (
        UniqueConstraint('organization_id', 'number', name='uq_legal_actions_org_number'),
        Index('idx_legal_action_org_status', 'organization_id', 'legal_status_id'),
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
    assigned_users = relationship(
        "User",
        secondary="legal_action_users",
        back_populates="assigned_legal_actions",
    )
    
    # Organização
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    organization = relationship("Organization", backref="legal_actions")
    
    # Tipo e status
    action_type_id = Column(Integer, ForeignKey("legal_action_types.id", ondelete="RESTRICT"), nullable=False)
    action_type = relationship("LegalActionType", back_populates="legal_actions")

    legal_status_id = Column(
        Integer,
        ForeignKey("legal_action_statuses.id", ondelete="RESTRICT"),
        nullable=False,
    )
    legal_status = relationship("LegalActionStatus", back_populates="legal_actions")
    
    # Tribunal / Localização
    court_name = Column(String)  # Nome legível do tribunal
    tribunal = Column(String, index=True)  # Alias DataJud (ex: "tjsp")
    comarca = Column(String)
    vara = Column(String)
    orgao_julgador = Column(String)
    competencia = Column(String)
    magistrado = Column(String)

    # Classe processual (TPU)
    classe_processual_codigo = Column(String, index=True)
    classe_processual_nome = Column(String)

    # Assuntos (JSON serializado: [{"codigo": "...", "nome": "..."}])
    assuntos_json = Column(Text)

    # Datas
    filing_date = Column(Date)  # data do ajuizamento (dataAjuizamento)
    data_distribuicao = Column(Date)  # dataHoraDistribuicao
    closing_date = Column(Date)

    # Financeiro
    valor_causa = Column(Numeric(15, 2))

    # Segredo de justiça
    segredo_justica = Column(Boolean, default=False)

    # Sincronização DataJud
    datajud_synced_at = Column(DateTime(timezone=True))  # última sync com CNJ
    datajud_last_update = Column(String)   # dataHoraUltimaAtualizacao do CNJ
    datajud_preserve_manual = Column(Boolean, default=False)  # proteger edições manuais

    # Relacionamentos DataJud
    partes = relationship("ProcessoParte", back_populates="legal_action", cascade="all, delete-orphan")
    movimentos = relationship("ProcessoMovimento", back_populates="legal_action", cascade="all, delete-orphan")

    # Metadados
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<LegalAction(id={self.id}, number='{self.number}', title='{self.title}', organization_id={self.organization_id})>"
