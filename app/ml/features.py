from typing import Tuple

import pandas as pd


def build_feature_matrices(
    train_df: pd.DataFrame,
    test_df: pd.DataFrame
) -> Tuple[pd.DataFrame, pd.Series, pd.DataFrame, pd.Series]:
    """
    Cria X/y para treino e teste com one-hot encoding.

    As features escolhidas refletem fatores jurídicos relevantes:
    - tribunal: diferenças de volume e eficiência entre tribunais
    - classe_processual: tipos processuais têm durações típicas distintas
    - area_juridica_principal: área jurídica influencia complexidade e tempo
    - ano_ajuizamento/mes_ajuizamento: sazonalidade e mudanças normativas
    """
    train_df = _prepare_dates(train_df.copy())
    test_df = _prepare_dates(test_df.copy())

    categorical_cols = ["tribunal", "classe_processual", "area_juridica_principal"]
    numeric_cols = ["ano_ajuizamento", "mes_ajuizamento"]

    train_df[categorical_cols] = train_df[categorical_cols].fillna("desconhecido")
    test_df[categorical_cols] = test_df[categorical_cols].fillna("desconhecido")

    train_df = pd.get_dummies(train_df, columns=categorical_cols, prefix=categorical_cols, dtype=int)
    test_df = pd.get_dummies(test_df, columns=categorical_cols, prefix=categorical_cols, dtype=int)

    # Garantir que teste tenha as mesmas colunas do treino
    test_df = test_df.reindex(columns=train_df.columns, fill_value=0)

    feature_cols = [
        col
        for col in train_df.columns
        if col not in (
            "duracao_dias",
            "data_ajuizamento",
            "numero_processo",
            "data_fim",
            "status_processo",
        )
    ]

    X_train = train_df[feature_cols]
    y_train = train_df["duracao_dias"]

    X_test = test_df[feature_cols]
    y_test = test_df["duracao_dias"]

    X_train = X_train[numeric_cols + [c for c in X_train.columns if c not in numeric_cols]]
    X_test = X_test[numeric_cols + [c for c in X_test.columns if c not in numeric_cols]]

    return X_train, y_train, X_test, y_test


def build_inference_matrix(
    features_input: dict,
    feature_columns: list[str]
) -> pd.DataFrame:
    """
    Constrói matriz de inferência compatível com o modelo treinado.
    """
    df = pd.DataFrame([features_input])
    df = _prepare_dates(df)

    categorical_cols = ["tribunal", "classe_processual", "area_juridica_principal"]
    df[categorical_cols] = df[categorical_cols].fillna("desconhecido")

    df = pd.get_dummies(df, columns=categorical_cols, prefix=categorical_cols, dtype=int)

    feature_df = df.reindex(columns=feature_columns, fill_value=0)
    return feature_df


def _prepare_dates(df: pd.DataFrame) -> pd.DataFrame:
    df["data_ajuizamento"] = pd.to_datetime(df["data_ajuizamento"], errors="coerce")
    df["ano_ajuizamento"] = df["data_ajuizamento"].dt.year
    df["mes_ajuizamento"] = df["data_ajuizamento"].dt.month
    return df
