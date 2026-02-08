from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.user import UserLogin, Token
from app.services.auth_service import AuthService

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
    
    return {
        "access_token": access_token,
        "token_type": "bearer"
    }
