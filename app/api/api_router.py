from fastapi import APIRouter

from app.api.endpoints import auth_router, users_router, clients_router, legal_actions_router, organizations_router

api_router = APIRouter()

# Incluir rotas de autenticação
api_router.include_router(
    auth_router,
    prefix="/auth",
    tags=["Autenticação"]
)

# Incluir rotas de organizações
api_router.include_router(
    organizations_router,
    prefix="/organizations",
    tags=["Organizações"]
)

# Incluir rotas de usuários
api_router.include_router(
    users_router,
    prefix="/users",
    tags=["Usuários"]
)

# Incluir rotas de clientes
api_router.include_router(
    clients_router,
    prefix="/clients",
    tags=["Clientes"]
)

# Incluir rotas de ações jurídicas
api_router.include_router(
    legal_actions_router,
    prefix="/legal-actions",
    tags=["Ações Jurídicas"]
)
