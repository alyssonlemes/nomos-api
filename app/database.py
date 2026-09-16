from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from app.core.config import settings


def _normalize_database_url(url: str) -> str:
    if url.startswith("postgres://"):
        return "postgresql://" + url[len("postgres://") :]
    return url


database_url = _normalize_database_url(settings.DATABASE_URL)
is_sqlite = database_url.startswith("sqlite")
uses_pgbouncer_pooler = "-pooler" in database_url

connect_args = {}
if not is_sqlite and "sslmode=" not in database_url:
    connect_args["sslmode"] = "require"

if is_sqlite:
    engine = create_engine(
        database_url,
        connect_args={"check_same_thread": False},
    )
elif uses_pgbouncer_pooler:
    # Neon pooled URL (PgBouncer) — NullPool evita pool duplo e conexões presas
    engine = create_engine(
        database_url,
        poolclass=NullPool,
        connect_args=connect_args,
    )
else:
    engine = create_engine(
        database_url,
        pool_pre_ping=True,
        pool_recycle=300,
        pool_size=5,
        max_overflow=10,
        connect_args=connect_args,
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """
    Dependency para obter sessão do banco de dados
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
