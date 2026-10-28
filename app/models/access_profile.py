from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, JSON, String, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class AccessProfile(Base):
    """Perfil de acesso de uma organização, com CRUD por módulo."""

    __tablename__ = "access_profiles"
    __table_args__ = (
        UniqueConstraint("organization_id", "name", name="uq_access_profile_org_name"),
    )

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    is_system = Column(Boolean, nullable=False, default=True)
    isolate_data = Column(Boolean, nullable=False, default=False)
    permissions = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    organization = relationship("Organization", backref="access_profiles")

    def __repr__(self):
        return f"<AccessProfile(id={self.id}, name='{self.name}', organization_id={self.organization_id})>"
