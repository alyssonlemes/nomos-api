from app.services.user_service import UserService
from app.services.auth_service import AuthService
from app.services.datajud_batch_service import DataJudBatchService
from app.services.process_analysis_service import ProcessAnalysisService

# Lazy import JurimetriaPredictionService to avoid loading sklearn at startup
def __getattr__(name):
    if name == "JurimetriaPredictionService":
        from app.services.jurimetria_prediction_service import JurimetriaPredictionService
        return JurimetriaPredictionService
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")

__all__ = [
    "UserService",
    "AuthService",
    "DataJudBatchService",
    "ProcessAnalysisService",
    "JurimetriaPredictionService",
]
