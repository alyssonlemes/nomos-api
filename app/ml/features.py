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
    - assunto_codigo: matéria jurídica influencia complexidade e tempo
    - ano_ajuizamento/mes_ajuizamento: sazonalidade e mudanças normativas
    """
    train_df = _prepare_dates(train_df.copy())
    test_df = _prepare_dates(test_df.copy())

    categorical_cols = ["tribunal", "classe_processual", "assunto_codigo"]
    numeric_cols = ["ano_ajuizamento", "mes_ajuizamento"]

    train_df[categorical_cols] = train_df[categorical_cols].fillna("desconhecido")
    test_df[categorical_cols] = test_df[categorical_cols].fillna("desconhecido")

    train_df = pd.get_dummies(train_df, columns=categorical_cols, prefix=categorical_cols, dtype=int)
    test_df = pd.get_dummies(test_df, columns=categorical_cols, prefix=categorical_cols, dtype=int)

    feature_cols = [col for col in train_df.columns if col not in ("tempo_tramitacao_dias", "data_ajuizamento", "numero_processo", "data_ultima_movimentacao")]

    X_train = train_df[feature_cols]
    y_train = train_df["tempo_tramitacao_dias"]

    X_test = test_df[feature_cols]
    X_test = X_test.reindex(columns=X_train.columns, fill_value=0)
    y_test = test_df["tempo_tramitacao_dias"]

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

    categorical_cols = ["tribunal", "classe_processual", "assunto_codigo"]
    df[categorical_cols] = df[categorical_cols].fillna("desconhecido")

    df = pd.get_dummies(df, columns=categorical_cols, prefix=categorical_cols, dtype=int)

    feature_df = df.reindex(columns=feature_columns, fill_value=0)
    return feature_df


def _prepare_dates(df: pd.DataFrame) -> pd.DataFrame:
    df["data_ajuizamento"] = pd.to_datetime(df["data_ajuizamento"], errors="coerce")
    df["ano_ajuizamento"] = df["data_ajuizamento"].dt.year
    df["mes_ajuizamento"] = df["data_ajuizamento"].dt.month
    return df
