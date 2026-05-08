from fastapi import APIRouter

from app.api.endpoints import (
    auth_router,
    users_router,
    clients_router,
    legal_actions_router,
    legal_action_types_router,
    legal_action_statuses_router,
    organizations_router,
    invitations_router,
    jurimetria_prediction_router,
    ml_router,
    dashboard_router,
    datajud_integration_router,
    process_analysis_router,
    activities_router,
)

api_router = APIRouter()

# Incluir rotas de autenticação
api_router.include_router(
    auth_router,
    prefix="/auth",
    tags=["Autenticação"],
)

# Incluir rotas de dashboard
api_router.include_router(
    dashboard_router,
    prefix="/dashboard",
    tags=["Dashboard"],
)

# Incluir rotas de organizações
api_router.include_router(
    organizations_router,
    prefix="/organizations",
    tags=["Organizações"],
)

# Incluir rotas de convites
api_router.include_router(
    invitations_router,
    prefix="/invitations",
    tags=["Convites"],
)

# Incluir rotas de usuários
api_router.include_router(
    users_router,
    prefix="/users",
    tags=["Usuários"],
)

# Incluir rotas de clientes
api_router.include_router(
    clients_router,
    prefix="/clients",
    tags=["Clientes"],
)

# Incluir rotas de ações jurídicas
api_router.include_router(
    legal_actions_router,
    prefix="/legal-actions",
    tags=["Ações Jurídicas"],
)

# Incluir rotas de tipos de ação jurídica (catálogo)
api_router.include_router(
    legal_action_types_router,
    prefix="/legal-action-types",
    tags=["Tipos de Ação Jurídica"],
)

# Incluir rotas de status de ação jurídica (catálogo)
api_router.include_router(
    legal_action_statuses_router,
    prefix="/legal-action-statuses",
    tags=["Status de Ação Jurídica"],
)

api_router.include_router(
    jurimetria_prediction_router,
    prefix="/jurimetria",
    tags=["Jurimetria"],
)

# Incluir rotas de ML
api_router.include_router(
    ml_router,
    prefix="/ml",
    tags=["Machine Learning"],
)

# Etapa 1 - Integração DataJud
api_router.include_router(
    datajud_integration_router,
    prefix="/integracao/datajud",
    tags=["Integração DataJud"],
)

# Análise de Processos Judiciais (IA)
api_router.include_router(
    process_analysis_router,
    prefix="/analise/processos",
    tags=["Análise de Processos"],
)

# Reuniões / Agendamentos
from app.api.endpoints.meetings import router as meetings_router

api_router.include_router(
    meetings_router,
    prefix="/meetings",
    tags=["Reuniões"],
)

# Atividades / Tarefas e Eventos (Kanban)
api_router.include_router(
    activities_router,
    prefix="/activities",
    tags=["Atividades"],
)
