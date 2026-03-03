from sqlalchemy import Column, Integer, String, Date, DateTime, Index, Text, UniqueConstraint
from sqlalchemy.sql import func

from app.database import Base


class JurimetriaDataset(Base):
    """
    Dataset de jurimetria pronto para consumo em ML e análise de processos.

    Campos originais mantidos para retrocompatibilidade.
    Campos novos adicionados para suportar análise conforme MD:
    - area_juridica_principal: classificação da área (Criminal, Família, Cível, etc.)
    - classe_principal_nome: nome legível da classe processual (TPU)
    - assuntos_json: JSON com lista de assuntos relacionados [{codigo, nome}, ...]
    - data_fim: data de encerramento inferida dos movimentos
    - status_processo: 'finalizado' | 'em_andamento'
    - movimento_encerramento: nome do movimento que determinou data_fim
    - duracao_dias: dias entre data_ajuizamento e data_fim (processos finalizados)
    """
    __tablename__ = "jurimetria_dataset"
    __table_args__ = (
        UniqueConstraint("tribunal", "numero_processo", name="uq_jurimetria_tribunal_numero"),
        Index("idx_jurimetria_tribunal_data", "tribunal", "data_ajuizamento"),
        Index("idx_jurimetria_classe_assunto", "classe_processual", "assunto_codigo"),
        Index("idx_jurimetria_area_juridica", "area_juridica_principal"),
        Index("idx_jurimetria_status", "status_processo"),
        Index("idx_jurimetria_area_status", "area_juridica_principal", "status_processo"),
    )

    id = Column(Integer, primary_key=True, index=True)
    tribunal = Column(String, nullable=False, index=True)
    numero_processo = Column(String, nullable=False, index=True)
    data_ajuizamento = Column(Date, nullable=False)
    classe_processual = Column(String, nullable=True)
    assunto_codigo = Column(String, nullable=True)

    # ── Campos adicionados para análise de processos (Seções 2-4 do MD) ──
    area_juridica_principal = Column(String, nullable=True)
    classe_principal_nome = Column(String, nullable=True)
    assuntos_json = Column(Text, nullable=True)  # JSON serializado
    data_fim = Column(Date, nullable=True)
    status_processo = Column(String, nullable=True, default="em_andamento")
    movimento_encerramento = Column(String, nullable=True)
    duracao_dias = Column(Integer, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self) -> str:
        return (
            f"<JurimetriaDataset(id={self.id}, "
            f"numero_processo='{self.numero_processo}', "
            f"area='{self.area_juridica_principal}', "
            f"status='{self.status_processo}')>"
        )
