from enum import Enum
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum as SQLEnum, UniqueConstraint, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class InvitationStatus(str, Enum):
    """Status de um convite"""
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


class Invitation(Base):
    """Modelo de Convite para organização"""
    __tablename__ = "invitations"
    __table_args__ = (
        UniqueConstraint('email', 'organization_id', 'status', name='uq_email_org_status'),
        Index('idx_invitation_email_status', 'email', 'status'),
        Index('idx_invitation_org_status', 'organization_id', 'status'),
    )

    id = Column(Integer, primary_key=True, index=True)
    
    # Quem foi convidado
    email = Column(String, index=True, nullable=False)
    
    # Para qual organização
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    organization = relationship("Organization", backref="invitations")
    
    # Quem convidou
    invited_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    invited_by = relationship("User", foreign_keys=[invited_by_id], backref="invitations_sent")
    
    # Status do convite
    status = Column(SQLEnum(InvitationStatus), default=InvitationStatus.PENDING, index=True)
    # Papel proposto para o usuário na organização (admin|member|viewer)
    role = Column(String, nullable=True, index=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<Invitation(id={self.id}, email='{self.email}', organization_id={self.organization_id}, status={self.status})>"
