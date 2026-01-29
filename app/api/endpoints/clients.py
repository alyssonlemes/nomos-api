from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.client import ClientCreate, ClientUpdate, ClientResponse, ClientListResponse, ClientStatus
from app.services.client_service import ClientService
from app.models.user import User
from app.api.deps import get_current_active_user

router = APIRouter()


@router.post(
    "",
    response_model=ClientResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Criar novo cliente"
)
def create_client(
    client_in: ClientCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Cria um novo cliente no sistema
    
    - **name**: Nome completo ou razão social
    - **email**: Email do cliente
    - **phone**: Telefone de contato
    - **document**: CPF ou CNPJ
    - **client_type**: Tipo (individual ou business)
    - **status**: Status inicial (prospect, active, etc)
    """
    # Verificar se documento já existe na organização
    if ClientService.get_by_document(db, document=client_in.document, organization_id=current_user.organization_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cliente com este documento já cadastrado"
        )
    
    client = ClientService.create(db=db, client_in=client_in, organization_id=current_user.organization_id, user_id=current_user.id)
    return client


@router.get(
    "",
    response_model=ClientListResponse,
    summary="Listar clientes"
)
def list_clients(
    skip: int = Query(0, ge=0, description="Número de registros a pular"),
    limit: int = Query(100, ge=1, le=500, description="Número máximo de registros"),
    status: Optional[ClientStatus] = Query(None, description="Filtrar por status"),
    search: Optional[str] = Query(None, description="Buscar por nome, email ou documento"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Lista todos os clientes da organização
    
    - **skip**: Paginação - registros a pular
    - **limit**: Paginação - máximo de registros
    - **status**: Filtro por status (active, inactive, prospect, archived)
    - **search**: Busca por nome, email, documento ou razão social
    """
    clients, total = ClientService.get_all(
        db,
        organization_id=current_user.organization_id,
        skip=skip,
        limit=limit,
        status=status,
        search=search
    )
    
    return ClientListResponse(total=total, clients=clients)


@router.get(
    "/statistics",
    summary="Estatísticas dos clientes"
)
def get_statistics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Retorna estatísticas dos clientes da organização
    
    - Total de clientes
    - Clientes ativos
    - Prospects
    - Inativos
    """
    stats = ClientService.get_statistics(db, organization_id=current_user.organization_id)
    return stats


@router.get(
    "/{client_id}",
    response_model=ClientResponse,
    summary="Buscar cliente por ID"
)
def get_client(
    client_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Busca um cliente específico por ID
    
    - **client_id**: ID do cliente
    """
    client = ClientService.get_by_id(db, client_id=client_id, organization_id=current_user.organization_id)
    
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cliente não encontrado"
        )
    
    return client


@router.put(
    "/{client_id}",
    response_model=ClientResponse,
    summary="Atualizar cliente"
)
def update_client(
    client_id: int,
    client_in: ClientUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Atualiza os dados de um cliente
    
    - **client_id**: ID do cliente
    - Todos os campos são opcionais
    """
    # Verificar se documento já existe (se foi fornecido)
    if client_in.document:
        existing_client = ClientService.get_by_document(
            db,
            document=client_in.document,
            organization_id=current_user.organization_id
        )
        if existing_client and existing_client.id != client_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cliente com este documento já cadastrado"
            )
    
    client = ClientService.update(
        db,
        client_id=client_id,
        client_in=client_in,
        organization_id=current_user.organization_id
    )
    
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cliente não encontrado"
        )
    
    return client


@router.delete(
    "/{client_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Deletar cliente"
)
def delete_client(
    client_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Deleta um cliente
    
    - **client_id**: ID do cliente
    """
    client = ClientService.delete(db, client_id=client_id, organization_id=current_user.organization_id)
    
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cliente não encontrado"
        )
    
    return None
