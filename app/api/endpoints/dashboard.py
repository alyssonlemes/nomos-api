from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.api.deps import exigir_permissao, get_data_filter_user_id, get_user_organization
from app.database import get_db
from app.models.user import User
from app.schemas.dashboard import DashboardStats
from app.services.dashboard_export import gerar_planilha
from app.services.dashboard_service import coletar_estatisticas

router = APIRouter()

@router.get(
    "/stats",
    response_model=DashboardStats,
    summary="Obter estatísticas do dashboard",
)
def get_dashboard_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(exigir_permissao("dashboard", "visualizar")),
    organization_id: int = Depends(get_user_organization),
    filter_user_id: int | None = Depends(get_data_filter_user_id),
):
    """Estatísticas da organização. Quem não administra vê só os próprios registros."""
    return coletar_estatisticas(db, current_user, organization_id, filter_user_id)

@router.get(
    "/export-excel",
    summary="Exportar planilha Excel com gráficos nativos dinâmicos",
)
def export_dashboard_excel(
    db: Session = Depends(get_db),
    current_user: User = Depends(exigir_permissao("dashboard", "visualizar")),
    organization_id: int = Depends(get_user_organization),
    filter_user_id: int | None = Depends(get_data_filter_user_id),
):
    conteudo, nome_arquivo = gerar_planilha(
        db, current_user, organization_id, filter_user_id
    )
    return Response(
        content=conteudo,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f'attachment; filename="{nome_arquivo}"',
            "Access-Control-Expose-Headers": "Content-Disposition",
        },
    )
