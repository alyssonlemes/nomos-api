from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone

from app.database import get_db
from app.schemas.user import UserLogin, Token
from app.services.auth_service import AuthService
from app.core.config import settings

router = APIRouter()


@router.post("/login", response_model=Token, summary="Login de usuário")
def login(
    login_data: UserLogin,
    db: Session = Depends(get_db)
):
    """
    Autentica um usuário e retorna um token JWT
    
    - **email**: Email do usuário
    - **password**: Senha do usuário
    """
    user = AuthService.authenticate_user(db, login_data)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou senha incorretos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = AuthService.create_token(user)
    
    # Calcular tempo de expiração
    expires_in_seconds = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": expires_in_seconds,
        "expires_at": expires_at
    }
