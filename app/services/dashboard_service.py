from datetime import datetime, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.perfis import tem_permissao_usuario
from app.models.client import Client
from app.models.legal_action import LegalAction
from app.models.legal_action_status import LegalActionStatus
from app.models.legal_action_type import LegalActionType
from app.models.user import User
from app.schemas.dashboard import DashboardStats

JANELA_RECENTE_DIAS = 30


def coletar_estatisticas(
    db: Session,
    current_user: User,
    organization_id: int,
    filter_user_id: int | None,
) -> DashboardStats:
    thirty_days_ago = datetime.now() - timedelta(days=JANELA_RECENTE_DIAS)
    client_filter = filter_user_id
    action_filter = filter_user_id
    if not tem_permissao_usuario(current_user, "clientes", "visualizar"):
        client_filter = -1
    if not tem_permissao_usuario(current_user, "processos", "visualizar"):
        action_filter = -1

    total_clients = db.query(func.count(Client.id)).filter(
        Client.organization_id == organization_id
    )
    if client_filter:
        total_clients = total_clients.filter(Client.user_id == client_filter)
    total_clients = total_clients.scalar()
    
    total_legal_actions = db.query(func.count(LegalAction.id)).filter(
        LegalAction.organization_id == organization_id
    )
    if action_filter:
        total_legal_actions = total_legal_actions.filter(LegalAction.user_id == action_filter)
    total_legal_actions = total_legal_actions.scalar()
    
    total_users = db.query(func.count(User.id)).filter(
        User.organization_id == organization_id
    ).scalar()
    
    actions_by_status_query = (
        db.query(LegalActionStatus.name, func.count(LegalAction.id))
        .join(LegalAction, LegalAction.legal_status_id == LegalActionStatus.id)
        .filter(LegalAction.organization_id == organization_id)
    )
    if action_filter:
        actions_by_status_query = actions_by_status_query.filter(LegalAction.user_id == action_filter)
    actions_by_status_query = actions_by_status_query.group_by(LegalActionStatus.id, LegalActionStatus.name).all()
    actions_by_status = {name: count for name, count in actions_by_status_query}
    
    actions_by_type_query = (
        db.query(LegalActionType.name, func.count(LegalAction.id))
        .join(LegalAction, LegalAction.action_type_id == LegalActionType.id)
        .filter(LegalAction.organization_id == organization_id)
    )
    if action_filter:
        actions_by_type_query = actions_by_type_query.filter(LegalAction.user_id == action_filter)
    actions_by_type_query = actions_by_type_query.group_by(LegalActionType.id, LegalActionType.name).all()
    actions_by_type = {name: count for name, count in actions_by_type_query}
    
    clients_by_status_query = db.query(
        Client.status,
        func.count(Client.id)
    ).filter(
        Client.organization_id == organization_id
    )
    if client_filter:
        clients_by_status_query = clients_by_status_query.filter(Client.user_id == client_filter)
    clients_by_status_query = clients_by_status_query.group_by(Client.status).all()
    clients_by_status = {status: count for status, count in clients_by_status_query}
    
    recent_clients = db.query(func.count(Client.id)).filter(
        Client.organization_id == organization_id,
        Client.created_at >= thirty_days_ago
    )
    if client_filter:
        recent_clients = recent_clients.filter(Client.user_id == client_filter)
    recent_clients = recent_clients.scalar()
    
    recent_actions = db.query(func.count(LegalAction.id)).filter(
        LegalAction.organization_id == organization_id,
        LegalAction.created_at >= thirty_days_ago
    )
    if action_filter:
        recent_actions = recent_actions.filter(LegalAction.user_id == action_filter)
    recent_actions = recent_actions.scalar()
    
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
