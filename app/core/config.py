from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """
    Configurações da aplicação
    """
    # API
    API_V1_PREFIX: str = "/api"
    PROJECT_NAME: str = "Nomos API"
    VERSION: str = "1.0.0"
    DESCRIPTION: str = "API REST com arquitetura escalável e autenticação JWT"
    
    # Security
    SECRET_KEY: str = "sua-chave-secreta-super-segura-mude-isso"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Database
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/nomos"
    
    # CORS
    BACKEND_CORS_ORIGINS: list = ["http://localhost:3000", "http://localhost:8080"]
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
