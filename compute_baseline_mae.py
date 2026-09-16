"""Calcula MAE/RMSE da baseline (mediana) no mesmo split temporal do treino."""
import json
from datetime import datetime

import numpy as np
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sqlalchemy import create_engine, text

from app.core.config import settings
from app.ml.dataset import load_jurimetria_dataset
from app.ml.features import build_feature_matrices
from app.ml.model_registry import load_active_model


def main() -> None:
    df = load_jurimetria_dataset()
    total_records = len(df)
    df = df.sort_values("data_ajuizamento")
    split_index = int(total_records * 0.8)
    train_df = df.iloc[:split_index]
    test_df = df.iloc[split_index:]

    X_train, y_train, X_test, y_test = build_feature_matrices(train_df, test_df)

    median_train = float(np.median(y_train))
    mean_train = float(np.mean(y_train))
    y_pred_median = np.full(shape=len(y_test), fill_value=median_train, dtype=float)
    y_pred_mean = np.full(shape=len(y_test), fill_value=mean_train, dtype=float)

    mae_median = float(mean_absolute_error(y_test, y_pred_median))
    rmse_median = float(np.sqrt(mean_squared_error(y_test, y_pred_median)))
    mae_mean = float(mean_absolute_error(y_test, y_pred_mean))
    rmse_mean = float(np.sqrt(mean_squared_error(y_test, y_pred_mean)))

    model, metadata = load_active_model()
    rf_eval = None
    if model is not None and metadata is not None:
        try:
            X_test_aligned = X_test.reindex(columns=metadata["feature_columns"], fill_value=0)
            preds = model.predict(X_test_aligned)
            rf_eval = {
                "mae": float(mean_absolute_error(y_test, preds)),
                "rmse": float(np.sqrt(mean_squared_error(y_test, preds))),
                "version": metadata.get("version"),
                "stored_mae": metadata.get("metrics", {}).get("mae"),
                "stored_rmse": metadata.get("metrics", {}).get("rmse"),
                "stored_total_records": metadata.get("total_records"),
            }
        except Exception as exc:
            rf_eval = {"error": str(exc)}

    engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
    with engine.connect() as conn:
        pg_version = conn.execute(text("SHOW server_version")).scalar()
        n_table = conn.execute(text("SELECT COUNT(*) FROM jurimetria_dataset")).scalar()
        n_valid = conn.execute(
            text("SELECT COUNT(*) FROM jurimetria_dataset WHERE duracao_dias IS NOT NULL")
        ).scalar()

    out = {
        "computed_at": datetime.now().isoformat(timespec="seconds"),
        "method": (
            "mesmo pipeline de train.py: ordenacao por data_ajuizamento, "
            "split temporal 80/20; baseline = mediana de y_train aplicada em y_test"
        ),
        "total_records_valid": int(total_records),
        "n_train": int(len(y_train)),
        "n_test": int(len(y_test)),
        "split_index": int(split_index),
        "y_train_median_dias": median_train,
        "y_train_mean_dias": mean_train,
        "y_train_min": float(np.min(y_train)),
        "y_train_max": float(np.max(y_train)),
        "y_test_median_dias": float(np.median(y_test)),
        "y_test_mean_dias": float(np.mean(y_test)),
        "baseline_median": {"mae": mae_median, "rmse": rmse_median},
        "baseline_mean": {"mae": mae_mean, "rmse": rmse_mean},
        "active_rf_reeval": rf_eval,
        "postgres_server_version": pg_version,
        "jurimetria_dataset_total_rows": int(n_table),
        "jurimetria_dataset_valid_duracao": int(n_valid),
    }
    print(json.dumps(out, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
