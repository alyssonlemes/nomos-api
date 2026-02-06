from fastapi import APIRouter

from app.api.endpoints import auth_router, users_router, clients_router, legal_actions_router, organizations_router, invitations_router, jurimetria_batch_router, jurimetria_prediction_router, ml_router

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

# Incluir rotas de convites
api_router.include_router(
    invitations_router,
    prefix="/invitations",
    tags=["Convites"]
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

# Incluir rotas de jurimetria
api_router.include_router(
    jurimetria_batch_router,
    prefix="/jurimetria",
    tags=["Jurimetria"]
)

api_router.include_router(
    jurimetria_prediction_router,
    prefix="/jurimetria",
    tags=["Jurimetria"]
)

# Incluir rotas de ML
api_router.include_router(
    ml_router,
    prefix="/ml",
    tags=["Machine Learning"]
)
