from sqlalchemy import Column, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


class LegalActionStatus(Base):
    """
    Catálogo de status jurídicos de ações.
    Referenciado por LegalAction via legal_status_id.
    """

    __tablename__ = "legal_action_statuses"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, index=True)
    code = Column(String(50), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)

    legal_actions = relationship("LegalAction", back_populates="legal_status")

    def __repr__(self) -> str:
        return f"<LegalActionStatus(id={self.id}, code='{self.code}', name='{self.name}')>"

