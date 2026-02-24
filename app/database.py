from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

# Criar engine do banco de dados
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

# Criar sessão
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base para os modelos
Base = declarative_base()

# Importar modelos para registrar as tabelas
from app.models.user import User  # noqa: F401,E402
from app.models.organization import Organization  # noqa: F401,E402
from app.models.invitation import Invitation  # noqa: F401,E402
from app.models.client import Client  # noqa: F401,E402
from app.models.legal_action import LegalAction  # noqa: F401,E402
from app.models.legal_action_type import LegalActionType  # noqa: F401,E402
from app.models.legal_action_status import LegalActionStatus  # noqa: F401,E402
from app.models.jurimetria_dataset import JurimetriaDataset  # noqa: F401,E402


def get_db():
    """
    Dependency para obter sessão do banco de dados
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
