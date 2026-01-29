from app.api.endpoints.auth import router as auth_router
from app.api.endpoints.users import router as users_router
from app.api.endpoints.clients import router as clients_router
from app.api.endpoints.legal_actions import router as legal_actions_router
from app.api.endpoints.organizations import router as organizations_router

__all__ = ["auth_router", "users_router", "clients_router", "legal_actions_router", "organizations_router"]
