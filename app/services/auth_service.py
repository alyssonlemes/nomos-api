from datetime import timedelta
from typing import Optional
from sqlalchemy.orm import Session

from app.models.user import User
from app.schemas.user import UserLogin
from app.services.user_service import UserService
from app.core.security import create_access_token
from app.core.config import settings


class AuthService:
    """
    Serviço de autenticação
    """
    
    @staticmethod
    def authenticate_user(db: Session, login_data: UserLogin) -> Optional[User]:
        """
        Autentica um usuário
        
        Args:
            db: Sessão do banco de dados
            login_data: Dados de login (email e password)
        
        Returns:
            Usuário autenticado ou None
        """
        return UserService.authenticate(
            db=db,
            email=login_data.email,
            password=login_data.password
        )
    
    @staticmethod
    def create_token(user: User) -> str:
        """
        Cria token JWT para o usuário
        
        Args:
            user: Usuário autenticado
        
        Returns:
            Token JWT
        """
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            subject=user.email,
            expires_delta=access_token_expires
        )
        return access_token
