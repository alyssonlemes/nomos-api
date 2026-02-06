from sqlalchemy import Column, Integer, String, Date, DateTime, Index, UniqueConstraint
from sqlalchemy.sql import func

from app.database import Base


class JurimetriaDataset(Base):
    """
    Dataset de jurimetria pronto para consumo em ML
    """
    __tablename__ = "jurimetria_dataset"
    __table_args__ = (
        UniqueConstraint("tribunal", "numero_processo", name="uq_jurimetria_tribunal_numero"),
        Index("idx_jurimetria_tribunal_data", "tribunal", "data_ajuizamento"),
        Index("idx_jurimetria_classe_assunto", "classe_processual", "assunto_codigo"),
    )

    id = Column(Integer, primary_key=True, index=True)
    tribunal = Column(String, nullable=False, index=True)
    numero_processo = Column(String, nullable=False, index=True)
    data_ajuizamento = Column(Date, nullable=False)
    data_ultima_movimentacao = Column(Date, nullable=True)
    tempo_tramitacao_dias = Column(Integer, nullable=True)
    classe_processual = Column(String, nullable=True)
    assunto_codigo = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self) -> str:
        return f"<JurimetriaDataset(id={self.id}, numero_processo='{self.numero_processo}')>"
