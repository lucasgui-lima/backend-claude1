"""Gestão de Chamados de Manutenção — API (FastAPI).

Executar em desenvolvimento:
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
Documentação interativa: http://localhost:8000/docs
"""
import logging
import traceback

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import CORS_ORIGINS, DATABASE_URL
from .database import Base, engine
from .routers import analytics, auth_router, cadastros, chamados, tv, users

logger = logging.getLogger("gestao-manutencao")
logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

# Cria as tabelas no banco de dados (apenas SQLite local).
# No PostgreSQL do Supabase, execute backend/supabase-schema.sql no SQL Editor
# para garantir tabelas + índices.
if DATABASE_URL.startswith("sqlite"):
    Base.metadata.create_all(bind=engine)
    logger.info("SQLite detectado — tabelas garantidas via create_all().")
else:
    logger.info(
        "PostgreSQL/Supabase detectado. Certifique-se de ter executado "
        "backend/supabase-schema.sql no SQL Editor para criar as tabelas e índices."
    )

app = FastAPI(
    title="Gestão de Chamados de Manutenção",
    version="1.0.0",
    description="API do aplicativo de gestão de chamados (mobile + TV).",
)

# CORS: navegadores rejeitam `allow_credentials=True` quando a origem é "*".
# Como o app autentica via Bearer no header Authorization (não via cookies),
# desligamos credentials quando estiver liberado para qualquer origem.
_libera_geral = "*" in CORS_ORIGINS or not CORS_ORIGINS
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS or ["*"],
    allow_credentials=not _libera_geral,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router.router)
app.include_router(users.router)
app.include_router(cadastros.router)
app.include_router(chamados.router)
app.include_router(analytics.router)
app.include_router(tv.router)


@app.exception_handler(Exception)
async def erro_inesperado(request: Request, exc: Exception):
    """Devolve JSON em qualquer erro não tratado, em vez de stacktrace HTML."""
    logger.exception("Erro não tratado em %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Erro interno do servidor. Tente novamente.",
            "error": str(exc),
        },
    )


@app.get("/", tags=["health"])
def health():
    return {"status": "ok", "app": "gestao-manutencao", "versao": "1.0.0"}


@app.get("/health/db", tags=["health"])
def health_db():
    """Verifica conectividade com o banco de dados."""
    from sqlalchemy import text
    from .database import SessionLocal
    try:
        db = SessionLocal()
        result = db.execute(text("SELECT 1")).scalar()
        db.close()
        return {"status": "ok", "database": "conectado", "result": result}
    except Exception as e:
        return {"status": "erro", "database": "falha", "error": str(e)}
