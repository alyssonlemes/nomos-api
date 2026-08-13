from app.api.endpoints.auth import router as auth_router
from app.api.endpoints.users import router as users_router
from app.api.endpoints.clients import router as clients_router
from app.api.endpoints.legal_actions import router as legal_actions_router
from app.api.endpoints.legal_action_types import router as legal_action_types_router
from app.api.endpoints.legal_action_statuses import router as legal_action_statuses_router
from app.api.endpoints.organizations import router as organizations_router
from app.api.endpoints.invitations import router as invitations_router
from app.api.endpoints.jurimetria_prediction import router as jurimetria_prediction_router
from app.api.endpoints.ml import router as ml_router
from app.api.endpoints.dashboard import router as dashboard_router
from app.api.endpoints.datajud_integration import router as datajud_integration_router
from app.api.endpoints.process_analysis import router as process_analysis_router
from app.api.endpoints.activities import router as activities_router
from app.api.endpoints.notifications import router as notifications_router

__all__ = [
    "auth_router",
    "users_router",
    "clients_router",
    "legal_actions_router",
    "legal_action_types_router",
    "legal_action_statuses_router",
    "organizations_router",
    "invitations_router",
    "jurimetria_prediction_router",
    "ml_router",
    "dashboard_router",
    "datajud_integration_router",
    "process_analysis_router",
    "activities_router",
    "notifications_router",
]
