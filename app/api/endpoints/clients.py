from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.client import ClientCreate, ClientUpdate, ClientResponse, ClientListResponse
from app.services.client_service import ClientService
from app.api.deps import get_current_active_user, get_user_organization

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
    current_user = Depends(get_current_active_user),
    organization_id: int = Depends(get_user_organization)
):
    """
    Cria um novo cliente vinculado à organização
    """
    if ClientService.get_by_document(db, document=client_in.document, organization_id=organization_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cliente com este documento já cadastrado"
        )
    
    return ClientService.create(db=db, client_in=client_in, organization_id=organization_id, user_id=current_user.id)


@router.get(
    "",
    response_model=ClientListResponse,
    summary="Listar clientes"
)
def list_clients(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    organization_id: int = Depends(get_user_organization)
):
    """
    Lista todos os clientes da organização
    """
    clients, total = ClientService.get_all(
        db,
        organization_id=organization_id,
        skip=skip,
        limit=limit,
        search=search
    )
    return ClientListResponse(total=total, clients=clients)



@router.get(
    "/{client_id}",
    response_model=ClientResponse,
    summary="Buscar cliente"
)
def get_client(
    client_id: int,
    db: Session = Depends(get_db),
    organization_id: int = Depends(get_user_organization)
):
    """
    Busca um cliente específico por ID
    """
    client = ClientService.get_by_id(db, client_id=client_id, organization_id=organization_id)
    
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
    organization_id: int = Depends(get_user_organization)
):
    """
    Atualiza os dados de um cliente
    """
    if client_in.document:
        existing = ClientService.get_by_document(
            db,
            document=client_in.document,
            organization_id=organization_id
        )
        if existing and existing.id != client_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cliente com este documento já cadastrado"
            )
    
    client = ClientService.update(
        db,
        client_id=client_id,
        client_in=client_in,
        organization_id=organization_id
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
    organization_id: int = Depends(get_user_organization)
):
    """
    Deleta um cliente da organização
    """
    client = ClientService.delete(db, client_id=client_id, organization_id=organization_id)
    
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cliente não encontrado"
        )

