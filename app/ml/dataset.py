from typing import List, Optional

import pandas as pd
from sqlalchemy import create_engine, text

from app.core.config import settings


COLUMNS: List[str] = [
    "tribunal",
    "numero_processo",
    "classe_processual",
    "area_juridica_principal",
    "data_ajuizamento",
    "duracao_dias",
]

COLUMNS_EXTENDED: List[str] = COLUMNS + [
    "data_fim",
    "status_processo",
]


def load_jurimetria_dataset(
    area_juridica: Optional[str] = None,
    use_extended: bool = False,
) -> pd.DataFrame:
    """
    Carrega o dataset de jurimetria com registros válidos para treino.

    Args:
        area_juridica: se informado, filtra por área jurídica específica
        use_extended: se True, inclui colunas adicionais da análise de processos
    """
    engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)

    columns = COLUMNS_EXTENDED if use_extended else COLUMNS
    columns_sql = ", ".join(columns)

    where_clauses = ["duracao_dias IS NOT NULL"]
    params = {}

    if area_juridica:
        where_clauses.append("area_juridica_principal = :area")
        params["area"] = area_juridica

    where_sql = " AND ".join(where_clauses)

    query = text(
        f"""
        SELECT {columns_sql}
          FROM jurimetria_dataset
         WHERE {where_sql}
        """
    )

    with engine.connect() as connection:
        df = pd.read_sql(query, connection, params=params)

    df = df[columns]

    # Remover registros sem duração
    df = df.dropna(subset=["duracao_dias"])

    return df
