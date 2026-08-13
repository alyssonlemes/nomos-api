from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class Notification(Base):
    """Notificacoes in-app para usuarios."""

    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    legal_action_id = Column(Integer, ForeignKey("legal_actions.id", ondelete="SET NULL"), nullable=True)
    title = Column(String, nullable=False)
    message = Column(String, nullable=False)
    read_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", backref="notifications")
    organization = relationship("Organization", backref="notifications")
    legal_action = relationship("LegalAction", backref="notifications")
