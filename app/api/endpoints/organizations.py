from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.organization import OrganizationCreate, OrganizationUpdate, OrganizationResponse, OrganizationWithStats
from app.schemas.user import UserResponse
from app.services.organization_service import OrganizationService
from app.services.user_service import UserService
from app.models.user import User
from app.api.deps import get_current_active_user

router = APIRouter()


@router.post(
    "",
    response_model=OrganizationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Criar nova organização"
)
def create_organization(
    org_in: OrganizationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Cria uma nova organização/escritório
    
    **Requer:** Usuário autenticado com permissões de superuser
    
    - **name**: Nome da organização/escritório
    - **document**: CNPJ (opcional)
    """
    # Apenas superusers podem criar organizações
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas superusers podem criar organizações"
        )
    
    # Verificar se documento já existe
    if org_in.document:
        existing_org = OrganizationService.get_by_document(db, document=org_in.document)
        if existing_org:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Organização com este documento já cadastrada"
            )
    
    organization = OrganizationService.create(db=db, org_in=org_in)
    return organization


@router.get(
    "",
    response_model=List[OrganizationResponse],
    summary="Listar organizações"
)
def list_organizations(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    is_active: Optional[bool] = Query(None, description="Filtrar por status ativo"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Lista todas as organizações
    
    **Requer:** Usuário autenticado com permissões de superuser
    
    - **skip**: Paginação - registros a pular
    - **limit**: Paginação - máximo de registros
    - **is_active**: Filtro por status (ativo/inativo)
    """
    # Apenas superusers podem listar todas as organizações
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas superusers podem listar organizações"
        )
    
    organizations = OrganizationService.get_all(db, skip=skip, limit=limit, is_active=is_active)
    return organizations


@router.get(
    "/me",
    response_model=OrganizationWithStats,
    summary="Obter organização atual"
)
def get_my_organization(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Retorna a organização do usuário autenticado com estatísticas
    """
    organization = OrganizationService.get_by_id(db, organization_id=current_user.organization_id)
    
    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organização não encontrada"
        )
    
    # Adicionar estatísticas
    stats = OrganizationService.get_statistics(db, organization_id=organization.id)
    
    org_dict = {
        "id": organization.id,
        "name": organization.name,
        "document": organization.document,
        "is_active": organization.is_active,
        "created_at": organization.created_at,
        "updated_at": organization.updated_at,
        **stats
    }
    
    return org_dict


@router.get(
    "/{organization_id}",
    response_model=OrganizationWithStats,
    summary="Buscar organização por ID"
)
def get_organization(
    organization_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Busca uma organização específica por ID
    
    **Requer:** Usuário autenticado com permissões de superuser
    
    - **organization_id**: ID da organização
    """
    # Apenas superusers podem visualizar qualquer organização
    if not current_user.is_superuser and current_user.organization_id != organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Você não tem permissão para acessar esta organização"
        )
    
    organization = OrganizationService.get_by_id(db, organization_id=organization_id)
    
    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organização não encontrada"
        )
    
    # Adicionar estatísticas
    stats = OrganizationService.get_statistics(db, organization_id=organization.id)
    
    org_dict = {
        "id": organization.id,
        "name": organization.name,
        "document": organization.document,
        "is_active": organization.is_active,
        "created_at": organization.created_at,
        "updated_at": organization.updated_at,
        **stats
    }
    
    return org_dict


@router.put(
    "/{organization_id}",
    response_model=OrganizationResponse,
    summary="Atualizar organização"
)
def update_organization(
    organization_id: int,
    org_in: OrganizationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Atualiza os dados de uma organização
    
    **Requer:** Usuário autenticado com permissões de superuser
    
    - **organization_id**: ID da organização
    - Todos os campos são opcionais
    """
    # Apenas superusers podem atualizar organizações
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas superusers podem atualizar organizações"
        )
    
    # Verificar se documento já existe (se foi fornecido)
    if org_in.document:
        existing_org = OrganizationService.get_by_document(db, document=org_in.document)
        if existing_org and existing_org.id != organization_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Organização com este documento já cadastrada"
            )
    
    organization = OrganizationService.update(db, organization_id=organization_id, org_in=org_in)
    
    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organização não encontrada"
        )
    
    return organization


@router.delete(
    "/{organization_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Deletar organização"
)
def delete_organization(
    organization_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Desativa uma organização (soft delete)
    
    **Requer:** Usuário autenticado com permissões de superuser
    
    - **organization_id**: ID da organização
    """
    # Apenas superusers podem deletar organizações
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas superusers podem deletar organizações"
        )
    
    organization = OrganizationService.delete(db, organization_id=organization_id)
    
    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organização não encontrada"
        )


@router.post(
    "/{organization_id}/users/{user_id}",
    response_model=UserResponse,
    summary="Vincular usuário à organização"
)
def add_user_to_organization(
    organization_id: int,
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Vincula um usuário a uma organização
    
    **Requer:** Usuário autenticado com permissões de superuser
    
    - **organization_id**: ID da organização
    - **user_id**: ID do usuário a ser vinculado
    """
    # Apenas superusers podem vincular usuários
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas superusers podem vincular usuários a organizações"
        )
    
    # Verificar se organização existe
    organization = OrganizationService.get_by_id(db, organization_id=organization_id)
    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organização não encontrada"
        )
    
    # Vincular usuário
    user = OrganizationService.add_user_to_organization(db, user_id=user_id, organization_id=organization_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado"
        )
    
    return user


@router.get(
    "/{organization_id}/users",
    response_model=List[UserResponse],
    summary="Listar usuários da organização"
)
def list_organization_users(
    organization_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Lista todos os usuários de uma organização
    
    **Requer:** Usuário pertencente à organização ou superuser
    
    - **organization_id**: ID da organização
    """
    # Validar permissões
    if not current_user.is_superuser and current_user.organization_id != organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Você não tem permissão para acessar os usuários desta organização"
        )
    
    # Verificar se organização existe
    organization = OrganizationService.get_by_id(db, organization_id=organization_id)
    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organização não encontrada"
        )
    
    users = UserService.get_all(db, organization_id=organization_id, skip=skip, limit=limit)
    return users
