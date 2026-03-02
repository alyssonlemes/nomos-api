from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.user import UserCreate, UserUpdate, UserResponse, UserRegisterWithOrg, UserRoleUpdate
from app.schemas.organization import OrganizationCreate
from app.services.user_service import UserService
from app.services.organization_service import OrganizationService
from app.models.user import User
from app.api.deps import get_current_active_user, require_write_access, get_admin_or_owner

router = APIRouter()


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar novo usuário (sem organização)"
)
def register(
    user_in: UserCreate,
    db: Session = Depends(get_db)
):
    """
    Cria um novo usuário no sistema SEM organização obrigatória
    
    Esta é a primeira etapa do fluxo:
    1. Criar conta aqui
    2. Login
    3. Depois criar/acessar organização
    
    - **email**: Email válido e único
    - **password**: Senha com no mínimo 6 caracteres
    - **full_name**: Nome completo (opcional)
    - **organization_id**: ID da organização (opcional - pode criar depois)
    """
    # Verificar se email já existe
    if UserService.get_by_email(db, email=user_in.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email já registrado"
        )
    
    # Se organization_id foi fornecido, validar se existe
    if user_in.organization_id:
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
    
    Requer que o usuário tenha uma organização criada.
    
    - **skip**: Número de registros a pular (paginação)
    - **limit**: Número máximo de registros a retornar
    """
    # Verificar se usuário tem organização
    if not current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Você precisa ter uma organização para acessar outros usuários. Crie uma organização primeiro."
        )
    
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
    
    Requer que o usuário tenha uma organização criada.
    
    - **user_id**: ID do usuário
    """
    # Verificar se usuário tem organização
    if not current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Você precisa ter uma organização para acessar outros usuários. Crie uma organização primeiro."
        )
    
    user = UserService.get_by_id(db, user_id=user_id, organization_id=current_user.organization_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado"
        )
    
    return user


@router.put("/{user_id}", response_model=UserResponse, summary="Atualizar usuário")
def update_user(
    user_id: int,
    user_in: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_write_access)
):
    """
    Atualiza os dados de um usuário (requer autenticação)
    
    Usuários só podem atualizar seus próprios dados.
    Nota: Atualização de email e senha não requer organização.
    
    - **user_id**: ID do usuário
    - Campos atualizáveis: email, full_name, password, is_active
    """
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
    
    # Para update do próprio usuário, organization_id pode ser None
    user = UserService.update(db, user_id=user_id, user_in=user_in, organization_id=current_user.organization_id or 0)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado"
        )
    
    return user


@router.patch(
    "/{user_id}/role",
    response_model=UserResponse,
    summary="Atualizar role do usuário"
)
def update_user_role(
    user_id: int,
    role_update: UserRoleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_or_owner)
):
    """
    Atualiza a role de um usuário da organização.
    
    **Apenas admins e owners podem realizar esta ação.**
    
    Roles disponíveis:
    - **admin**: Acesso total, pode gerenciar usuários e configurações
    - **member**: Acesso normal, pode criar e editar dados
    - **viewer**: Apenas visualização, sem permissões de escrita
    - **assistant**: Acesso a tudo exceto processos e jurimetria
    
    - **user_id**: ID do usuário a ter a role atualizada
    - **role**: Nova role a ser atribuída
    """
    # Verificar se usuário tem organização
    if not current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Você precisa ter uma organização."
        )
    
    # Buscar o usuário alvo
    target_user = UserService.get_by_id(db, user_id=user_id, organization_id=current_user.organization_id)
    
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado na sua organização"
        )
    
    # Não permitir alterar a própria role
    if target_user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Você não pode alterar sua própria role"
        )
    
    # Atualizar a role
    updated_user = UserService.update_role(
        db=db,
        user_id=user_id,
        role_update=role_update,
        organization_id=current_user.organization_id
    )
    
    if not updated_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Erro ao atualizar usuário"
        )
    
    return updated_user


@router.post(
    "/{user_id}/unlink-organization",
    response_model=UserResponse,
    summary="Desvincular usuário da organização"
)
def unlink_organization(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_write_access)
):
    """
    Desvincula o usuário da organização definindo `organization_id` como None.

    Usuários só podem desvincular seus próprios perfis, a menos que sejam superuser.
    """
    # Buscar usuário alvo (sem filtragem por organização para checar permissões)
    target_user = db.query(User).filter(User.id == user_id).first()

    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado"
        )

    # Permissões: o próprio usuário, superuser, ou admin/owner da mesma organização
    if current_user.id == user_id:
        org_param = current_user.organization_id
    elif UserService.is_superuser(current_user):
        org_param = None
    elif (current_user.role or "").lower() in ["admin", "owner"] and target_user.organization_id == current_user.organization_id:
        org_param = current_user.organization_id
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Você não tem permissão para desvincular este usuário"
        )

    user = UserService.unlink_organization(db=db, user_id=user_id, organization_id=org_param)

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
    current_user: User = Depends(require_write_access)
):
    """
    Deleta um usuário (requer autenticação)
    
    Usuários só podem deletar seus próprios perfis.
    Nota: Pode deletar mesmo sem organização.
    
    - **user_id**: ID do usuário
    """
    # Verificar se é o próprio usuário
    if current_user.id != user_id and not UserService.is_superuser(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Você só pode deletar seu próprio perfil"
        )
    
    # Para delete do próprio usuário, organization_id pode ser None
    user = UserService.delete(db, user_id=user_id, organization_id=current_user.organization_id or 0)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado"
        )
    
    return None
