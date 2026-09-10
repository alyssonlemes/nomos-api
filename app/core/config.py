from typing import Any, Optional

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Configurações da aplicação
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # API
    API_V1_PREFIX: str = "/api/v1"
    PROJECT_NAME: str = "Nomos API"
    VERSION: str = "1.0.0"
    DESCRIPTION: str = "API REST com arquitetura escalável e autenticação JWT"

    # Security
    SECRET_KEY: str = "sua-chave-secreta-super-segura-mude-isso"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 horas

    # Database (Neon em produção)
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/nomos"

    # DataJud
    DATAJUD_API_KEY: Optional[str] = None

    # Frontend publicado (ex: https://nomos-web.onrender.com)
    FRONTEND_URL: Optional[str] = None

    # CORS — JSON array ou lista separada por vírgula
    BACKEND_CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:8080",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
        "http://127.0.0.1:8080",
    ]

    # Libera previews/deploys no Render sem precisar listar cada URL
    CORS_ALLOW_ORIGIN_REGEX: Optional[str] = r"https://.*\.onrender\.com"

    @field_validator("CORS_ALLOW_ORIGIN_REGEX", mode="before")
    @classmethod
    def empty_regex_to_none(cls, value: Any) -> Optional[str]:
        if value is None:
            return None
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: Any) -> list[str]:
        if value is None or value == "":
            return []
        if isinstance(value, list):
            return [str(origin).strip().rstrip("/") for origin in value if str(origin).strip()]
        if isinstance(value, str):
            stripped = value.strip()
            if stripped.startswith("["):
                import json

                parsed = json.loads(stripped)
                return [str(origin).strip().rstrip("/") for origin in parsed if str(origin).strip()]
            return [
                origin.strip().rstrip("/")
                for origin in stripped.split(",")
                if origin.strip()
            ]
        return value

    def get_cors_origins(self) -> list[str]:
        origins = [origin.rstrip("/") for origin in self.BACKEND_CORS_ORIGINS]
        if self.FRONTEND_URL:
            frontend = self.FRONTEND_URL.strip().rstrip("/")
            if frontend and frontend not in origins:
                origins.append(frontend)
        return origins


settings = Settings()
