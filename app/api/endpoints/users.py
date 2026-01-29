from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.user import UserCreate, UserUpdate, UserResponse, UserRegisterWithOrg
from app.schemas.organization import OrganizationCreate
from app.services.user_service import UserService
from app.services.organization_service import OrganizationService
from app.models.user import User
from app.api.deps import get_current_active_user

router = APIRouter()


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar novo usuário"
)
def register(
    user_in: UserCreate,
    db: Session = Depends(get_db)
):
    """
    Cria um novo usuário no sistema em uma organização existente
    
    - **email**: Email válido e único
    - **username**: Username único (3-50 caracteres)
    - **password**: Senha com no mínimo 6 caracteres
    - **full_name**: Nome completo (opcional)
    - **organization_id**: ID da organização existente
    """
    # Verificar se email já existe
    if UserService.get_by_email(db, email=user_in.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email já registrado"
        )
    
    # Verificar se username já existe
    if UserService.get_by_username(db, username=user_in.username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username já registrado"
        )
    
    # Verificar se a organização existe
    organization = OrganizationService.get_by_id(db, organization_id=user_in.organization_id)
    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organização não encontrada"
        )
    
    user = UserService.create(db=db, user_in=user_in)
    return user


@router.post(
    "/register-with-organization",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar novo usuário com organização"
)
def register_with_organization(
    user_in: UserRegisterWithOrg,
    db: Session = Depends(get_db)
):
    """
    Cria um novo usuário E uma nova organização simultaneamente
    
    Ideal para o primeiro usuário de um novo escritório
    
    - **email**: Email válido e único
    - **username**: Username único (3-50 caracteres)
    - **password**: Senha com no mínimo 6 caracteres
    - **full_name**: Nome completo (opcional)
    - **organization_name**: Nome da nova organização/escritório
    - **organization_document**: CNPJ da organização (opcional)
    """
    # Verificar se email já existe
    if UserService.get_by_email(db, email=user_in.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email já registrado"
        )
    
    # Verificar se username já existe
    if UserService.get_by_username(db, username=user_in.username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username já registrado"
        )
    
    # Verificar se documento da organização já existe
    if user_in.organization_document:
        existing_org = OrganizationService.get_by_document(db, document=user_in.organization_document)
        if existing_org:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Organização com este documento já cadastrada"
            )
    
    # Criar organização
    org_data = OrganizationCreate(
        name=user_in.organization_name,
        document=user_in.organization_document
    )
    organization = OrganizationService.create(db=db, org_in=org_data)
    
    # Criar usuário vinculado à nova organização
    user_data = UserCreate(
        email=user_in.email,
        username=user_in.username,
        password=user_in.password,
        full_name=user_in.full_name,
        organization_id=organization.id
    )
    user = UserService.create(db=db, user_in=user_data)
    
    return user


@router.get("/me", response_model=UserResponse, summary="Obter usuário atual")
def get_me(
    current_user: User = Depends(get_current_active_user)
):
    """
    Retorna as informações do usuário autenticado
    """
    return current_user


@router.get("", response_model=List[UserResponse], summary="Listar usuários")
def list_users(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Lista todos os usuários da mesma organização (requer autenticação)
    
    - **skip**: Número de registros a pular (paginação)
    - **limit**: Número máximo de registros a retornar
    """
    users = UserService.get_all(db, organization_id=current_user.organization_id, skip=skip, limit=limit)
    return users


@router.get("/{user_id}", response_model=UserResponse, summary="Buscar usuário por ID")
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Busca um usuário específico por ID da mesma organização (requer autenticação)
    
    - **user_id**: ID do usuário
    """
    user = UserService.get_by_id(db, user_id=user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado"
        )
    
    # Validar se o usuário pertence à mesma organização
    if user.organization_id != current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Você não tem permissão para acessar este usuário"
        )
    
    return user


@router.put("/{user_id}", response_model=UserResponse, summary="Atualizar usuário")
def update_user(
    user_id: int,
    user_in: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Atualiza os dados de um usuário (requer autenticação)
    
    Usuários só podem atualizar seus próprios dados ou de usuários da mesma organização
    
    - **user_id**: ID do usuário
    - Campos atualizáveis: email, username, full_name, password, is_active
    """
    # Buscar usuário alvo
    target_user = UserService.get_by_id(db, user_id=user_id)
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado"
        )
    
    # Validar se pertence à mesma organização
    if target_user.organization_id != current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Você não tem permissão para atualizar este usuário"
        )
    
    # Verificar se é o próprio usuário
    if current_user.id != user_id and not UserService.is_superuser(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Você só pode atualizar seu próprio perfil"
        )
    
    # Verificar se email já existe (se foi fornecido)
    if user_in.email:
        existing_user = UserService.get_by_email(db, email=user_in.email)
        if existing_user and existing_user.id != user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email já registrado"
            )
    
    # Verificar se username já existe (se foi fornecido)
    if user_in.username:
        existing_user = UserService.get_by_username(db, username=user_in.username)
        if existing_user and existing_user.id != user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username já registrado"
            )
    
    user = UserService.update(db, user_id=user_id, user_in=user_in)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado"
        )
    
    return user


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Deletar usuário"
)
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Deleta um usuário (requer autenticação)
    
    Usuários só podem deletar seus próprios perfis ou de usuários da mesma organização
    
    - **user_id**: ID do usuário
    """
    # Buscar usuário alvo
    target_user = UserService.get_by_id(db, user_id=user_id)
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado"
        )
    
    # Validar se pertence à mesma organização
    if target_user.organization_id != current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Você não tem permissão para deletar este usuário"
        )
    
    # Verificar se é o próprio usuário
    if current_user.id != user_id and not UserService.is_superuser(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Você só pode deletar seu próprio perfil"
        )
    
    user = UserService.delete(db, user_id=user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado"
        )
    
    return None
