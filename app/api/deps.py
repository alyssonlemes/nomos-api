from typing import Any
from jose import jwt, JWTError, ExpiredSignatureError
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.config import settings
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
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Dependency para garantir que o usuário está ativo
    
    Args:
        current_user: Usuário atual
    
    Returns:
        Usuário ativo
    
    Raises:
        HTTPException: Se o usuário estiver inativo
    """
    if not UserService.is_active(current_user):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Usuário inativo"
        )
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


def get_admin_or_owner(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> User:
    """
    Dependency para garantir que o usuário é admin ou owner da organização
    
    Args:
        current_user: Usuário ativo
        db: Sessão do banco de dados
    
    Returns:
        Usuário com permissões de admin/owner
    
    Raises:
        HTTPException: Se o usuário não tiver permissões
    """
    if not current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Você precisa ter uma organização."
        )
    
    # Verificar se é admin ou owner (case-insensitive)
    if (current_user.role or "").lower() in ["admin", "owner"]:
        return current_user
    
    # Verificar se é o owner da organização
    from app.services.organization_service import OrganizationService
    organization = OrganizationService.get_by_id(db, organization_id=current_user.organization_id)
    
    if organization and organization.owner_id == current_user.id:
        return current_user
    
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Apenas administradores ou proprietários podem realizar esta ação."
    )
