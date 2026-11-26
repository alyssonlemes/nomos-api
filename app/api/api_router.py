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
    notifications_router,
    access_profiles_router,
    jurimai_callback_router,
)

api_router = APIRouter()

api_router.include_router(
    auth_router,
    prefix="/auth",
    tags=["Autenticação"],
)

api_router.include_router(
    dashboard_router,
    prefix="/dashboard",
    tags=["Dashboard"],
)

api_router.include_router(
    organizations_router,
    prefix="/organizations",
    tags=["Organizações"],
)

api_router.include_router(
    invitations_router,
    prefix="/invitations",
    tags=["Convites"],
)

api_router.include_router(
    users_router,
    prefix="/users",
    tags=["Usuários"],
)

api_router.include_router(
    clients_router,
    prefix="/clients",
    tags=["Clientes"],
)

api_router.include_router(
    legal_actions_router,
    prefix="/legal-actions",
    tags=["Ações Jurídicas"],
)

api_router.include_router(
    legal_action_types_router,
    prefix="/legal-action-types",
    tags=["Tipos de Ação Jurídica"],
)

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

api_router.include_router(
    ml_router,
    prefix="/ml",
    tags=["Machine Learning"],
)

api_router.include_router(
    datajud_integration_router,
    prefix="/integracao/datajud",
    tags=["Integração DataJud"],
)

api_router.include_router(
    process_analysis_router,
    prefix="/analise/processos",
    tags=["Análise de Processos"],
)

api_router.include_router(
    activities_router,
    prefix="/activities",
    tags=["Atividades"],
)

api_router.include_router(
    notifications_router,
    prefix="/notifications",
    tags=["Notificacoes"],
)

api_router.include_router(
    access_profiles_router,
    prefix="/access-profiles",
    tags=["Perfis de acesso"],
)

api_router.include_router(
    jurimai_callback_router,
    prefix="/integracao/juri",
    tags=["Acompanhamento de processos"],
)
