from typing import List

import pandas as pd
from sqlalchemy import create_engine, text

from app.core.config import settings


COLUMNS: List[str] = [
    "tribunal",
    "numero_processo",
    "classe_processual",
    "assunto_codigo",
    "data_ajuizamento",
    "data_ultima_movimentacao",
    "tempo_tramitacao_dias"
]


def load_jurimetria_dataset() -> pd.DataFrame:
    """
    Carrega o dataset de jurimetria com registros válidos para treino.
    """
    engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)

    query = text(
        """
        SELECT tribunal,
               numero_processo,
               classe_processual,
               assunto_codigo,
               data_ajuizamento,
               data_ultima_movimentacao,
               tempo_tramitacao_dias
          FROM jurimetria_dataset
         WHERE tempo_tramitacao_dias IS NOT NULL
        """
    )

    with engine.connect() as connection:
        df = pd.read_sql(query, connection)

    df = df[COLUMNS]
    return df
