"""Conexão com o banco de dados via SQLAlchemy.

Funciona com:
  - SQLite (desenvolvimento local)
  - PostgreSQL via Supabase (produção)
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from .config import DATABASE_URL

eh_sqlite = DATABASE_URL.startswith("sqlite")
connect_args = {"check_same_thread": False} if eh_sqlite else {}

# Em PostgreSQL (Supabase), pool_recycle evita usar conexões que já foram
# encerradas pelo servidor por inatividade (acontece no plano gratuito).
engine_kwargs = dict(
    connect_args=connect_args,
    pool_pre_ping=True,
)
if not eh_sqlite:
    engine_kwargs.update(
        pool_size=5,
        max_overflow=10,
        pool_recycle=1800,   # recicla conexões a cada 30 min
        pool_timeout=30,
    )

engine = create_engine(DATABASE_URL, **engine_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """Dependency do FastAPI: abre e fecha a sessão por requisição."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
