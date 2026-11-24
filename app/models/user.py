from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.perfis import isola_dados_usuario, nome_perfil, permissoes_efetivas_usuario
from app.database import Base

class User(Base):
    """
    Modelo de Usuário
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    role = Column(String, nullable=True)  # Espelho legado do perfil, usado pelo painel e por clientes antigos
    profile_id = Column(Integer, ForeignKey("access_profiles.id", ondelete="SET NULL"), nullable=True, index=True)
    profile = relationship("AccessProfile", lazy="joined")

    # Organização (opcional até criar uma)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True)
    organization = relationship("Organization", foreign_keys=[organization_id], backref="users")
    assigned_legal_actions = relationship(
        "LegalAction",
        secondary="legal_action_users",
        back_populates="assigned_users",
    )
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    @property
    def profile_name(self):
        return nome_perfil(self)

    @property
    def isolate_data(self):
        return isola_dados_usuario(self)

    @property
    def permissions(self):
        return permissoes_efetivas_usuario(self)

    def __repr__(self):
        return f"<User(id={self.id}, email='{self.email}')>"

from app.models.access_profile import AccessProfile  # noqa: E402,F401
