from pydantic import BaseModel
from typing import Dict


class DashboardStats(BaseModel):
    """Schema de resposta para estatísticas do dashboard"""
    total_clients: int
    total_legal_actions: int
    total_users: int
    actions_by_status: Dict[str, int]
    actions_by_type: Dict[str, int]
    clients_by_status: Dict[str, int]
    recent_clients_30d: int
    recent_actions_30d: int
