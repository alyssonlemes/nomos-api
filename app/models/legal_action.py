from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum, ForeignKey, Text, Date
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

from app.database import Base


class LegalActionType(str, enum.Enum):
    """Tipos de ações jurídicas"""
    LABOR = "labor"              # Trabalhista
    CIVIL = "civil"              # Cível
    CRIMINAL = "criminal"        # Criminal
    ADMINISTRATIVE = "admin"     # Administrativa
    TAX = "tax"                  # Tributária
    COMMERCIAL = "commercial"    # Comercial
    FAMILY = "family"            # Família
    REAL_ESTATE = "real_estate"  # Imóvel
    OTHER = "other"              # Outra


class LegalStatus(str, enum.Enum):
    """Status jurídico do processo"""
    PRE_TRIAL = "pre_trial"          # Pré-processual
    FILING = "filing"                # Ajuizamento
    LITIGATION = "litigation"        # Contencioso
    EXECUTION = "execution"          # Execução
    APPEAL = "appeal"                # Recurso
    FINALIZED = "finalized"          # Finalizado
    ARCHIVED = "archived"            # Arquivado


class PartyType(str, enum.Enum):
    """Tipo de parte no processo"""
    PLAINTIFF = "plaintiff"      # Autor
    DEFENDANT = "defendant"      # Réu
    THIRD_PARTY = "third_party"  # Terceiro
    APPELLANT = "appellant"      # Apelante
    APPELLEE = "appellee"        # Apelado


class MovementType(str, enum.Enum):
    """Tipo de movimentação"""
    FILING = "filing"
    HEARING = "hearing"
    DECISION = "decision"
    APPEAL = "appeal"
    JUDGMENT = "judgment"
    COMPLIANCE = "compliance"
    NOTIFICATION = "notification"
    OTHER = "other"


class DeadlineStatus(str, enum.Enum):
    """Status do prazo"""
    PENDING = "pending"
    COMPLETED = "completed"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"


class LegalAction(Base):
    """
    Modelo de Ação Jurídica / Processo
    """
    __tablename__ = "legal_actions"

    id = Column(Integer, primary_key=True, index=True)
    
    # Informações básicas
    number = Column(String, unique=True, index=True, nullable=False)  # Número do processo
    title = Column(String, nullable=False)
    description = Column(Text)
    
    # Relacionamentos
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    client = relationship("Client", backref="legal_actions")
    
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # Advogado responsável
    user = relationship("User", backref="legal_actions")
    
    # Tipo e status
    action_type = Column(Enum(LegalActionType), nullable=False)
    legal_status = Column(Enum(LegalStatus), default=LegalStatus.PRE_TRIAL, nullable=False)
    
    # Tribunal
    court_name = Column(String)
    court_segment = Column(String)  # Vara, Juzgado, etc
    
    # Datas
    filing_date = Column(Date)
    closing_date = Column(Date)
    
    # Metadados
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relacionamentos
    parties = relationship("Party", backref="legal_action", cascade="all, delete-orphan")
    movements = relationship("CaseMovement", backref="legal_action", cascade="all, delete-orphan")
    deadlines = relationship("Deadline", backref="legal_action", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<LegalAction(id={self.id}, number='{self.number}', title='{self.title}')>"


class Party(Base):
    """
    Modelo de Partes no Processo
    """
    __tablename__ = "parties"

    id = Column(Integer, primary_key=True, index=True)
    
    # Relacionamento
    legal_action_id = Column(Integer, ForeignKey("legal_actions.id"), nullable=False)
    
    # Informações
    name = Column(String, nullable=False, index=True)
    party_type = Column(Enum(PartyType), nullable=False)
    
    # Contato
    email = Column(String)
    phone = Column(String)
    document = Column(String)  # CPF ou CNPJ
    
    # Representação
    legal_representative = Column(String)  # Nome do advogado/representante
    
    # Metadados
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<Party(id={self.id}, name='{self.name}', party_type='{self.party_type}')>"


class CaseMovement(Base):
    """
    Modelo de Movimentações/Andamentos do Processo
    """
    __tablename__ = "case_movements"

    id = Column(Integer, primary_key=True, index=True)
    
    # Relacionamento
    legal_action_id = Column(Integer, ForeignKey("legal_actions.id"), nullable=False)
    
    # Informações
    title = Column(String, nullable=False)
    description = Column(Text)
    movement_type = Column(Enum(MovementType), nullable=False)
    
    # Datas
    movement_date = Column(Date, nullable=False, index=True)
    notification_date = Column(Date)
    
    # Fonte
    source = Column(String)  # Tribunal, Ofício, etc
    
    # Metadados
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<CaseMovement(id={self.id}, legal_action_id={self.legal_action_id}, movement_type='{self.movement_type}')>"


class Deadline(Base):
    """
    Modelo de Prazos do Processo
    """
    __tablename__ = "deadlines"

    id = Column(Integer, primary_key=True, index=True)
    
    # Relacionamento
    legal_action_id = Column(Integer, ForeignKey("legal_actions.id"), nullable=False)
    
    # Informações
    title = Column(String, nullable=False)
    description = Column(Text)
    deadline_type = Column(String)  # Moção, Apelação, Contestação, etc
    
    # Datas
    due_date = Column(Date, nullable=False, index=True)
    completion_date = Column(Date)
    
    # Status
    status = Column(Enum(DeadlineStatus), default=DeadlineStatus.PENDING, nullable=False)
    
    # Metadados
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<Deadline(id={self.id}, legal_action_id={self.legal_action_id}, due_date='{self.due_date}')>"
