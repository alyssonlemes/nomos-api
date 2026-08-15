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
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 horas
    
    # Database
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/nomos"

    # DataJud
    DATAJUD_API_KEY: Optional[str] = None
    
    # CORS
    BACKEND_CORS_ORIGINS: list = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:8080",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
        "http://127.0.0.1:8080",
    ]
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
