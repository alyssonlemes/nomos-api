from typing import Any
from jose import jwt, JWTError
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
        HTTPException: Se o token for inválido ou o usuário não for encontrado
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Não foi possível validar as credenciais",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        token = credentials.credentials
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = UserService.get_by_username(db, username=username)
    if user is None:
        raise credentials_exception
    
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
