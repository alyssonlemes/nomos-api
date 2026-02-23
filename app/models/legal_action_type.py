from sqlalchemy import Column, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


class LegalActionType(Base):
    """
    Catálogo de tipos de ações jurídicas (CRUD próprio).
    Referenciado por LegalAction via action_type_id.
    """
    __tablename__ = "legal_action_types"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, index=True)
    code = Column(String(50), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)

    legal_actions = relationship("LegalAction", back_populates="action_type")

    def __repr__(self):
        return f"<LegalActionType(id={self.id}, code='{self.code}', name='{self.name}')>"
