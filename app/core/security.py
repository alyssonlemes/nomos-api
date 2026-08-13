from datetime import datetime, timedelta, timezone
from typing import Optional, Any
from jose import jwt
import bcrypt
from passlib.context import CryptContext

from app.core.config import settings

# Patch passlib/bcrypt 4.0+ compatibility issue
if not hasattr(bcrypt, "__about__"):
    bcrypt.__about__ = bcrypt

# Contexto para hash de senhas
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def create_access_token(subject: str | Any, expires_delta: Optional[timedelta] = None) -> str:
    """
    Cria um token JWT
    
    Args:
        subject: Identificador do usuário (email ou id)
        expires_delta: Tempo de expiração do token
    
    Returns:
        Token JWT codificado
    """
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    
    to_encode = {"exp": expire, "sub": str(subject)}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifica se a senha corresponde ao hash
    
    Args:
        plain_password: Senha em texto plano
        hashed_password: Hash da senha armazenada
    
    Returns:
        True se a senha está correta, False caso contrário
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    Gera hash da senha
    
    Args:
        password: Senha em texto plano
    
    Returns:
        Hash bcrypt da senha
    """
    return pwd_context.hash(password)
