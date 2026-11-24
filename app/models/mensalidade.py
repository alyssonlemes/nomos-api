from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.sql import func

from app.database import Base


class Mensalidade(Base):
    """Pagamento mensal de um escritório. Só o painel interno lê e grava esta tabela."""

    __tablename__ = "mensalidades"
    __table_args__ = (UniqueConstraint("organization_id", "competencia", name="uq_mensalidade_competencia"),)

    id = Column(Integer, primary_key=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    competencia = Column(Date, nullable=False)
    valor_centavos = Column(Integer, nullable=False)
    pago_em = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
