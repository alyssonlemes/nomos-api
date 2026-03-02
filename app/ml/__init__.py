# Lazy imports to avoid loading sklearn at startup due to Windows AppControl policy
# These will be imported only when actually needed

__all__ = [
    "load_jurimetria_dataset",
    "build_feature_matrices",
    "train_pipeline",
    "evaluate_model",
    "save_model",
    "get_active_model_info"
]
