import json
import os
from datetime import datetime
from typing import Dict, Optional, Tuple

import joblib


BASE_DIR = os.path.dirname(__file__)
REGISTRY_DIR = os.path.join(BASE_DIR, "models")
ACTIVE_FILE = os.path.join(REGISTRY_DIR, "active_model.json")


def save_model(model, metrics: Dict[str, float], total_records: int, feature_columns: list[str]) -> str:
    """
    Salva o modelo e metadata com versionamento por timestamp.
    """
    os.makedirs(REGISTRY_DIR, exist_ok=True)

    version = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    version_dir = os.path.join(REGISTRY_DIR, version)
    os.makedirs(version_dir, exist_ok=True)

    model_path = os.path.join(version_dir, "model.joblib")
    metadata_path = os.path.join(version_dir, "metadata.json")

    joblib.dump(model, model_path)

    metadata = {
        "version": version,
        "trained_at": datetime.utcnow().isoformat(),
        "total_records": total_records,
        "metrics": metrics,
        "feature_columns": feature_columns,
        "active": True
    }

    with open(metadata_path, "w", encoding="utf-8") as file:
        json.dump(metadata, file, ensure_ascii=False, indent=2)

    _set_active_model(version)
    return version


def _set_active_model(version: str) -> None:
    payload = {
        "version": version,
        "updated_at": datetime.utcnow().isoformat()
    }
    with open(ACTIVE_FILE, "w", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=False, indent=2)


def get_active_model_info() -> Optional[Dict[str, str]]:
    if not os.path.exists(ACTIVE_FILE):
        return None
    with open(ACTIVE_FILE, "r", encoding="utf-8") as file:
        return json.load(file)


def load_active_model() -> Tuple[Optional[object], Optional[Dict[str, object]]]:
    """
    Carrega o modelo ativo e sua metadata.
    """
    active_info = get_active_model_info()
    if not active_info:
        return None, None

    version = active_info.get("version")
    if not version:
        return None, None

    version_dir = os.path.join(REGISTRY_DIR, version)
    model_path = os.path.join(version_dir, "model.joblib")
    metadata_path = os.path.join(version_dir, "metadata.json")

    if not os.path.exists(model_path) or not os.path.exists(metadata_path):
        return None, None

    model = joblib.load(model_path)
    with open(metadata_path, "r", encoding="utf-8") as file:
        metadata = json.load(file)

    return model, metadata
