from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum, ForeignKey, Text, UniqueConstraint, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

from app.database import Base


class ClientType(str, enum.Enum):
    """Tipo de cliente"""
    INDIVIDUAL = "individual"  # Pessoa física
    BUSINESS = "business"      # Pessoa jurídica


class ClientStatus(str, enum.Enum):
    """Status do cliente"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    PROSPECT = "prospect"
    ARCHIVED = "archived"


class Client(Base):
    """Modelo de Cliente vinculado a uma Organização"""
    __tablename__ = "clients"
    __table_args__ = (
        UniqueConstraint('document', 'organization_id', name='uq_client_document_org'),
        Index('idx_client_org_status', 'organization_id', 'status'),
    )

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    email = Column(String, index=True)
    phone = Column(String)
    document = Column(String, index=True, nullable=False)
    client_type = Column(Enum(ClientType), default=ClientType.INDIVIDUAL, nullable=False)
    status = Column(Enum(ClientStatus), default=ClientStatus.PROSPECT, nullable=False)
    
    # Endereço
    address = Column(String)
    city = Column(String)
    state = Column(String)
    zip_code = Column(String)
    
    # Informações adicionais
    company_name = Column(String)  # Para pessoa jurídica
    
    # Organização (obrigatório)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    organization = relationship("Organization", backref="clients")
    
    # Usuário responsável (opcional)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    user = relationship("User", backref="clients")
    
    # Metadados
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<Client(id={self.id}, name='{self.name}', document='{self.document}')>"
