from typing import Dict, Tuple

import pandas as pd
from sklearn.ensemble import RandomForestRegressor

from app.ml.dataset import load_jurimetria_dataset
from app.ml.features import build_feature_matrices
from app.ml.evaluate import evaluate_model
from app.ml.model_registry import save_model


MIN_TRAINING_RECORDS = 500


def train_pipeline(min_records: int = MIN_TRAINING_RECORDS) -> Tuple[str, Dict[str, float], int]:
    """
    Executa o pipeline completo de treino com split temporal.
    """
    df = load_jurimetria_dataset()
    total_records = len(df)

    if total_records < min_records:
        raise ValueError("Registros insuficientes para treino")

    df = df.sort_values("data_ajuizamento")
    split_index = int(total_records * 0.8)
    train_df = df.iloc[:split_index]
    test_df = df.iloc[split_index:]

    X_train, y_train, X_test, y_test = build_feature_matrices(train_df, test_df)

    # RandomForest funciona bem com dados heterogêneos, captura não linearidades
    # e entrega baseline robusto sem forte tuning inicial.
    model = RandomForestRegressor(
        n_estimators=300,
        max_depth=None,
        min_samples_split=2,
        min_samples_leaf=1,
        random_state=42,
        n_jobs=-1
    )

    model.fit(X_train, y_train)

    metrics = evaluate_model(model, X_test, y_test)
    version = save_model(model, metrics, total_records, list(X_train.columns))

    return version, metrics, total_records
