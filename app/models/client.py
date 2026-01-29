from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum, ForeignKey, Text
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
    """
    Modelo de Cliente
    """
    __tablename__ = "clients"

    id = Column(Integer, primary_key=True, index=True)
    
    # Informações básicas
    name = Column(String, nullable=False, index=True)
    email = Column(String, index=True)
    phone = Column(String)
    document = Column(String, unique=True, index=True)  # CPF ou CNPJ
    
    # Tipo e status
    client_type = Column(Enum(ClientType), default=ClientType.INDIVIDUAL, nullable=False)
    status = Column(Enum(ClientStatus), default=ClientStatus.PROSPECT, nullable=False)
    
    # Endereço
    address = Column(String)
    city = Column(String)
    state = Column(String)
    zip_code = Column(String)
    
    # Informações adicionais
    notes = Column(Text)
    company_name = Column(String)  # Para pessoa jurídica
    
    # Relacionamento com usuário (advogado responsável)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    user = relationship("User", backref="clients")
    
    # Organização
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    organization = relationship("Organization", backref="clients")
    
    # Metadados
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<Client(id={self.id}, name='{self.name}', document='{self.document}')>"
