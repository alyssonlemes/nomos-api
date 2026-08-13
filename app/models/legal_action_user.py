from sqlalchemy import Column, Integer, ForeignKey, DateTime, UniqueConstraint
from sqlalchemy.sql import func

from app.database import Base


class LegalActionUser(Base):
    """Vinculo entre usuarios e processos (many-to-many)."""

    __tablename__ = "legal_action_users"
    __table_args__ = (
        UniqueConstraint("legal_action_id", "user_id", name="uq_legal_action_user"),
    )

    id = Column(Integer, primary_key=True, index=True)
    legal_action_id = Column(Integer, ForeignKey("legal_actions.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
