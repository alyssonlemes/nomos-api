from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import IntegrityError

from app.core.config import settings
from app.database import engine, Base
from app.api import api_router

# Criar todas as tabelas no banco de dados automaticamente
# Isso lê todos os models e cria as tabelas se não existirem
Base.metadata.create_all(bind=engine)

# Criar aplicação FastAPI
app = FastAPI(
    title=settings.PROJECT_NAME,
    description=settings.DESCRIPTION,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Incluir routers da API v1
app.include_router(api_router, prefix=settings.API_V1_PREFIX)


@app.exception_handler(IntegrityError)
async def handle_integrity_error(request: Request, exc: IntegrityError):
    return JSONResponse(
        status_code=400,
        content={
            "detail": "Erro de integridade no banco de dados",
            "error": str(exc.orig)
        }
    )


@app.get("/", tags=["Root"])
def root():
    """
    Endpoint raiz - informações básicas da API
    """
    return {
        "message": f"Bem-vindo à {settings.PROJECT_NAME}",
        "version": settings.VERSION,
        "docs": "/docs",
        "redoc": "/redoc",
        "api_v1": settings.API_V1_PREFIX
    }


@app.get("/health", tags=["Health"])
def health_check():
    """
    Health check endpoint
    """
    return {
        "status": "healthy",
        "version": settings.VERSION
    }


if __name__ == "__main__":
    import uvicorn
    # Trigger uvicorn reload again
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
