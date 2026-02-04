from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.organization import OrganizationCreate, OrganizationUpdate, OrganizationResponse
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
    summary="Criar organização"
)
def create_organization(
    org_in: OrganizationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Cria uma nova organização vinculada ao usuário autenticado (Etapa 2 do fluxo).
    
    O usuário que cria a organização vira o proprietário dela.
    Após criar a organização, o usuário pode convidar outras pessoas.
    
    **Fluxo esperado:**
    1. Registrar conta (POST /api/v1/users/register)
    2. Fazer login (POST /api/v1/auth/login)
    3. Criar organização AQUI (POST /api/v1/organizations)
    4. Convidar usuários ou acessar outras telas
    """
    # Validar se usuário já tem organização
    if current_user.organization_id is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Você já possui uma organização. Não é possível criar outra."
        )
    
    # Verificar se documento já existe
    if org_in.document:
        existing_org = OrganizationService.get_by_document(db, document=org_in.document)
        if existing_org:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Organização com este documento já cadastrada"
            )
    
    # Criar organização
    organization = OrganizationService.create(db=db, org_in=org_in, owner_id=current_user.id)
    
    # Vincular usuário à organização automaticamente
    current_user.organization_id = organization.id
    db.commit()
    db.refresh(current_user)
    
    return organization


@router.get(
    "",
    response_model=OrganizationResponse,
    summary="Obter organização do usuário"
)
def get_my_organization(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Retorna a organização do usuário autenticado.
    """
    if not current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Você ainda não possui uma organização. Crie uma primeiro."
        )
    
    organization = OrganizationService.get_by_id(db, organization_id=current_user.organization_id)
    
    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organização não encontrada"
        )
    
    return organization


@router.put(
    "",
    response_model=OrganizationResponse,
    summary="Atualizar organização"
)
def update_organization(
    org_in: OrganizationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Atualiza os dados da organização do usuário.
    """
    if not current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Você não possui uma organização"
        )
    
    # Verificar se documento já existe (se foi fornecido)
    if org_in.document:
        existing_org = OrganizationService.get_by_document(db, document=org_in.document)
        if existing_org and existing_org.id != current_user.organization_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Organização com este documento já cadastrada"
            )
    
    organization = OrganizationService.update(
        db, 
        organization_id=current_user.organization_id, 
        org_in=org_in
    )
    
    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organização não encontrada"
        )
    
    return organization


@router.get(
    "/users",
    response_model=list[UserResponse],
    summary="Listar usuários da organização"
)
def list_organization_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Lista todos os usuários da organização do usuário autenticado.
    """
    if not current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Você não possui uma organização"
        )
    
    users = UserService.get_all(db, organization_id=current_user.organization_id)
    return users
