from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.user import UserCreate, UserUpdate, UserResponse, UserRoleUpdate, UserListResponse
from app.schemas.organization import OrganizationCreate
from app.services.user_service import UserService
from app.services.organization_service import OrganizationService
from app.services.access_profile_service import AcessoNegado, AccessProfileService, PerfilInvalido
from app.models.user import User
from app.api.deps import get_current_active_user, exigir_permissao
from app.core.perfis import eh_administrador, isola_dados_usuario, tem_permissao_usuario

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


@router.get("/me", response_model=UserResponse, summary="Obter usuário atual")
def get_me(
    current_user: User = Depends(get_current_active_user)
):
    """
    Retorna as informações do usuário autenticado
    """
    return current_user


@router.get("", response_model=UserListResponse, summary="Listar usuários")
def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=500),
    search: Optional[str] = Query(None, description="Buscar por nome ou e-mail"),
    is_active: Optional[bool] = Query(None, description="Filtrar por status ativo/inativo"),
    role: Optional[str] = Query(None, description="Filtrar pelo papel legado"),
    profile_id: Optional[int] = Query(None, description="Filtrar por perfil"),
    sort_by: Optional[str] = Query(None, description="Campo de ordenação"),
    sort_dir: Optional[str] = Query("desc", description="Direção: asc ou desc"),
    db: Session = Depends(get_db),
    current_user: User = Depends(exigir_permissao("usuarios", "visualizar"))
):
    """
    Lista os usuários da mesma organização, de 10 em 10 por padrão.
    """
    if not current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Você precisa ter uma organização para acessar outros usuários. Crie uma organização primeiro."
        )

    users, total = UserService.get_all(
        db,
        organization_id=current_user.organization_id,
        skip=skip,
        limit=limit,
        search=search,
        is_active=is_active,
        role=role,
        profile_id=profile_id,
        only_user_id=current_user.id if isola_dados_usuario(current_user) else None,
        sort_by=sort_by,
        sort_dir=sort_dir,
    )
    return UserListResponse(total=total, users=users, skip=skip, limit=limit)


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

    if current_user.id != user_id and not tem_permissao_usuario(current_user, "usuarios", "visualizar"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Você não tem permissão para acessar este recurso.",
        )

    if isola_dados_usuario(current_user) and current_user.id != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuário não encontrado")

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
    
    Usuários só podem atualizar seus próprios dados,
    exceto quem tem permissão de editar usuários na organização.
    """
    is_self = current_user.id == user_id
    is_superuser = UserService.is_superuser(current_user)

    if not is_self and not is_superuser:
        if not current_user.organization_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Você precisa ter uma organização."
            )
        if not tem_permissao_usuario(current_user, "usuarios", "editar"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Você não tem permissão para atualizar outros usuários."
            )

    target = db.query(User).filter(User.id == user_id).first()
    if target and not is_self and not is_superuser and eh_administrador(target) and not eh_administrador(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas o administrador pode alterar outro administrador.",
        )

    if target and user_in.is_active is False and eh_administrador(target):
        if AccessProfileService.contar_administradores(db, target.organization_id, excluir_id=target.id) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Não é possível inativar o último administrador da organização.",
            )
    
    # Verificar se email já existe (se foi fornecido)
    if user_in.email:
        existing_user = UserService.get_by_email(db, email=user_in.email)
        if existing_user and existing_user.id != user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email já registrado"
            )
    
    organization_id = None if is_superuser else current_user.organization_id
    user = UserService.update(db, user_id=user_id, user_in=user_in, organization_id=organization_id)
    
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
    current_user: User = Depends(exigir_permissao("usuarios", "editar"))
):
    """
    Atribui um perfil de acesso ao usuário.

    O administrador pode atribuir qualquer perfil. Os demais só alteram
    perfis que não sejam Administrador, e nunca o próprio.
    """
    if not current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Você precisa ter uma organização."
        )

    target_user = UserService.get_by_id(db, user_id=user_id, organization_id=current_user.organization_id)
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado na sua organização"
        )

    profile_id = role_update.profile_id
    if profile_id is None and role_update.role:
        perfil = AccessProfileService.resolver_por_papel(db, current_user.organization_id, role_update.role)
        if perfil is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Perfil inválido para esta organização.")
        profile_id = perfil.id

    try:
        return AccessProfileService.atribuir(db, current_user, target_user, profile_id)
    except AcessoNegado as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    except PerfilInvalido as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.post(
    "/{user_id}/unlink-organization",
    response_model=UserResponse,
    summary="Desvincular usuário da organização"
)
def unlink_organization(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Desvincula o usuário da organização.

    A própria pessoa pode sair. Quem tem permissão de excluir usuários pode
    desvincular os demais, exceto o último administrador.
    """
    target_user = db.query(User).filter(User.id == user_id).first()

    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado"
        )

    if current_user.id == user_id:
        org_param = current_user.organization_id
    elif UserService.is_superuser(current_user):
        org_param = None
    elif (
        tem_permissao_usuario(current_user, "usuarios", "excluir")
        and target_user.organization_id == current_user.organization_id
    ):
        if eh_administrador(target_user) and not eh_administrador(current_user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Apenas o administrador pode desvincular outro administrador.",
            )
        org_param = current_user.organization_id
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Você não tem permissão para desvincular este usuário"
        )

    if target_user.organization_id and eh_administrador(target_user):
        if AccessProfileService.contar_administradores(db, target_user.organization_id, excluir_id=target_user.id) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Não é possível desvincular o último administrador da organização.",
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
    current_user: User = Depends(get_current_active_user)
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
