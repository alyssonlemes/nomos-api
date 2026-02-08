from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta

from app.database import get_db
from app.schemas.dashboard import DashboardStats
from app.models.user import User
from app.models.client import Client
from app.models.legal_action import LegalAction
from app.api.deps import get_current_active_user, get_user_organization

router = APIRouter()


@router.get(
    "/stats",
    response_model=DashboardStats,
    summary="Obter estatísticas do dashboard"
)
def get_dashboard_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    organization_id: int = Depends(get_user_organization)
):
    """
    Retorna estatísticas consolidadas para o dashboard
    
    Inclui:
    - Total de clientes, ações e usuários
    - Distribuição de ações por status e tipo
    - Distribuição de clientes por status
    - Novos registros nos últimos 30 dias
    """
    # Data de 30 dias atrás
    thirty_days_ago = datetime.now() - timedelta(days=30)
    
    # Total de clientes
    total_clients = db.query(func.count(Client.id)).filter(
        Client.organization_id == organization_id
    ).scalar()
    
    # Total de ações jurídicas
    total_legal_actions = db.query(func.count(LegalAction.id)).filter(
        LegalAction.organization_id == organization_id
    ).scalar()
    
    # Total de usuários da organização
    total_users = db.query(func.count(User.id)).filter(
        User.organization_id == organization_id
    ).scalar()
    
    # Ações por status
    actions_by_status_query = db.query(
        LegalAction.legal_status,
        func.count(LegalAction.id)
    ).filter(
        LegalAction.organization_id == organization_id
    ).group_by(LegalAction.legal_status).all()
    
    actions_by_status = {status: count for status, count in actions_by_status_query}
    
    # Ações por tipo
    actions_by_type_query = db.query(
        LegalAction.action_type,
        func.count(LegalAction.id)
    ).filter(
        LegalAction.organization_id == organization_id
    ).group_by(LegalAction.action_type).all()
    
    actions_by_type = {action_type: count for action_type, count in actions_by_type_query}
    
    # Clientes por status
    clients_by_status_query = db.query(
        Client.status,
        func.count(Client.id)
    ).filter(
        Client.organization_id == organization_id
    ).group_by(Client.status).all()
    
    clients_by_status = {status: count for status, count in clients_by_status_query}
    
    # Clientes criados nos últimos 30 dias
    recent_clients = db.query(func.count(Client.id)).filter(
        Client.organization_id == organization_id,
        Client.created_at >= thirty_days_ago
    ).scalar()
    
    # Ações criadas nos últimos 30 dias
    recent_actions = db.query(func.count(LegalAction.id)).filter(
        LegalAction.organization_id == organization_id,
        LegalAction.created_at >= thirty_days_ago
    ).scalar()
    
    return DashboardStats(
        total_clients=total_clients or 0,
        total_legal_actions=total_legal_actions or 0,
        total_users=total_users or 0,
        actions_by_status=actions_by_status,
        actions_by_type=actions_by_type,
        clients_by_status=clients_by_status,
        recent_clients_30d=recent_clients or 0,
        recent_actions_30d=recent_actions or 0
    )
