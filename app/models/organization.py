from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class Organization(Base):
    """Modelo de Organização - Escritório de advocacia"""
    __tablename__ = "organizations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    document = Column(String, unique=True, index=True, nullable=True)  # CNPJ - opcional
    legal_representative_name = Column(String, nullable=True)
    legal_representative_document = Column(String, nullable=True)
    
    # Proprietário (quem criou)
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    owner = relationship("User", foreign_keys=[owner_id], backref="owned_organization")
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<Organization(id={self.id}, name='{self.name}', owner_id={self.owner_id})>"
