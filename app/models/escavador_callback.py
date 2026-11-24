from sqlalchemy import Column, DateTime, Integer, String
from sqlalchemy.sql import func

from app.database import Base

class EscavadorCallback(Base):
    """Registro do uuid do callback para tratar reentrega sem duplicar aviso."""

    __tablename__ = "escavador_callbacks"

    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(String(80), unique=True, nullable=False, index=True)
    event = Column(String(64), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
