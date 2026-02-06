from typing import Dict

import numpy as np
from sklearn.metrics import mean_absolute_error, mean_squared_error


def evaluate_model(model, X_test, y_test) -> Dict[str, float]:
    """
    Avalia o modelo com MAE e RMSE.

    Impacto jurídico:
    - MAE indica o erro médio em dias na previsão do tempo total.
    - RMSE penaliza grandes erros, críticos para decisões estratégicas.
    """
    predictions = model.predict(X_test)
    mae = mean_absolute_error(y_test, predictions)
    rmse = np.sqrt(mean_squared_error(y_test, predictions))

    return {
        "mae": float(mae),
        "rmse": float(rmse)
    }
