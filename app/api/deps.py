from typing import Any
from jose import jwt, JWTError, ExpiredSignatureError
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.config import settings
from app.core.perfis import eh_administrador, eh_gestor, isola_dados_usuario, tem_permissao_usuario
from app.services.user_service import UserService
from app.models.user import User

security = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    Dependency para obter o usuário atual a partir do token JWT
    
    Args:
        credentials: Credenciais Bearer token
        db: Sessão do banco de dados
    
    Returns:
        Usuário autenticado
    
    Raises:
        HTTPException: Se o token for inválido ou o usuário não ser encontrado
    """
    try:
        token = credentials.credentials
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        email: str = payload.get("sub")
        if email is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token inválido: dados incompletos",
                headers={"WWW-Authenticate": "Bearer"},
            )
    except ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expirado. Faça login novamente.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido. Não foi possível validar as credenciais.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user = UserService.get_by_email(db, email=email)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário não encontrado",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user


def get_current_active_user(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    """
    Dependency para garantir que o usuário está ativo e vinculado ao perfil da organização.
    """
    if not UserService.is_active(current_user):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Usuário inativo"
        )
    if current_user.organization_id and not current_user.profile_id:
        from app.services.access_profile_service import AccessProfileService
        current_user = AccessProfileService.garantir_vinculo(db, current_user)
    return current_user


def get_current_superuser(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Dependency para garantir que o usuário é superusuário
    
    Args:
        current_user: Usuário atual
    
    Returns:
        Superusuário
    
    Raises:
        HTTPException: Se o usuário não for superusuário
    """
    if not UserService.is_superuser(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Privilégios insuficientes"
        )
    return current_user


def get_user_organization(
    current_user: User = Depends(get_current_active_user)
) -> int:
    """
    Dependency para garantir que o usuário tem uma organização
    
    Args:
        current_user: Usuário ativo
    
    Returns:
        ID da organização do usuário
    
    Raises:
        HTTPException: Se o usuário não tiver uma organização
    """
    if not current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Você precisa ter uma organização. Crie uma organização primeiro."
        )
    return current_user.organization_id


def exigir_permissao(modulo: str, acao: str = "visualizar"):
    """Exige a ação de CRUD no módulo do perfil do usuário."""

    def _dependencia(
        current_user: User = Depends(get_current_active_user),
    ) -> User:
        if current_user.is_superuser:
            return current_user
        if not tem_permissao_usuario(current_user, modulo, acao):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Você não tem permissão para acessar este recurso.",
            )
        return current_user

    return _dependencia


def get_admin_or_owner(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> User:
    """
    Garante gestão de usuários: administrador, gestor ou quem pode criar/editar usuários.
    """
    if current_user.is_superuser:
        return current_user

    if not current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Você precisa ter uma organização."
        )

    if (
        eh_administrador(current_user)
        or eh_gestor(current_user)
        or tem_permissao_usuario(current_user, "usuarios", "criar")
        or tem_permissao_usuario(current_user, "usuarios", "editar")
    ):
        return current_user

    from app.services.organization_service import OrganizationService
    organization = OrganizationService.get_by_id(db, organization_id=current_user.organization_id)
    if organization and organization.owner_id == current_user.id:
        return current_user

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Você não tem permissão para gerenciar usuários."
    )


def require_legal_actions_access(
    current_user: User = Depends(exigir_permissao("processos", "visualizar"))
) -> User:
    """Compatibilidade: visualizar processos."""
    return current_user


def require_write_access(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """
    Compatibilidade para escrita genérica.
    Bloqueia quem só visualiza clientes, processos e atividades.
    """
    if current_user.is_superuser or eh_administrador(current_user):
        return current_user
    pode_escrever = any(
        tem_permissao_usuario(current_user, modulo, acao)
        for modulo in ("clientes", "processos", "atividades", "usuarios", "configuracoes")
        for acao in ("criar", "editar", "excluir")
    )
    if not pode_escrever:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Você não tem permissão para alterar dados.",
        )
    return current_user


def get_data_filter_user_id(
    current_user: User = Depends(get_current_active_user)
) -> int | None:
    """
    Retorna o id do usuário quando o perfil isola os dados.
    Administrador e perfis sem isolamento recebem None e enxergam a organização.
    """
    if isola_dados_usuario(current_user):
        return current_user.id
    return None