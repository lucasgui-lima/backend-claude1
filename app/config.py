"""Configurações centrais do backend.

Variáveis de ambiente (obrigatórias em produção):
  DATABASE_URL  → PostgreSQL do Supabase
                  ex.: postgresql+psycopg2://postgres:[PASSWORD]@[HOST]:5432/postgres
                  IMPORTANTE: caracteres especiais na senha (@, #, /, etc.)
                  devem ser percent-encoded (ex.: @ → %40).
  SECRET_KEY    → chave longa e aleatória (ex.: `openssl rand -hex 32`)
  CORS_ORIGINS  → origens permitidas (separadas por vírgula)
"""
import os
import re
import warnings
from urllib.parse import quote_plus

from dotenv import load_dotenv

load_dotenv()

# ----------------------------- Segurança / JWT -----------------------------
_DEFAULT_SECRET = "TROQUE-ESTA-CHAVE-EM-PRODUCAO-9f8a7b6c"
SECRET_KEY = os.getenv("SECRET_KEY", _DEFAULT_SECRET)
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "720"))  # 12h

if SECRET_KEY == _DEFAULT_SECRET and os.getenv("ENV", "dev") == "prod":
    raise RuntimeError(
        "SECRET_KEY não foi definida em produção. "
        "Defina a variável de ambiente SECRET_KEY com um valor aleatório longo."
    )
if SECRET_KEY == _DEFAULT_SECRET:
    warnings.warn(
        "SECRET_KEY padrão em uso — apropriado apenas para desenvolvimento.",
        RuntimeWarning,
        stacklevel=2,
    )


def _corrigir_senha_url(url: str) -> str:
    """Garante que a senha na URL esteja percent-encoded.

    O SQLAlchemy usa o primeiro '@' como separador userinfo/host — se a senha
    contiver '@' sem encoding, a URL é interpretada erradamente.
    """
    idx_ultimo_arroba = url.rfind("@")
    if idx_ultimo_arroba == -1:
        return url
    idx_esquema = url.find("://")
    if idx_esquema == -1:
        return url
    userinfo = url[idx_esquema + 3:idx_ultimo_arroba]
    resto = url[idx_ultimo_arroba + 1:]
    colon = userinfo.find(":")
    if colon == -1:
        return url
    senha = userinfo[colon + 1:]
    if not senha or "%" in senha:
        return url
    senha_corrigida = quote_plus(senha)
    if senha_corrigida == senha:
        return url
    return f"{url[:idx_esquema + 3]}{userinfo[:colon + 1]}{senha_corrigida}@{resto}"


# ------------------------------- Banco de dados ----------------------------
def _montar_database_url() -> str:
    """Monta a URL do banco com a senha percent-encoded.

    Em produção, prefira DATABASE_URL completa via variável de ambiente.
    A senha aqui está percent-encoded (@ → %40) — sem isso, o parser do
    SQLAlchemy interpreta o '@' como separador de host e a conexão falha.
    """
    url = os.getenv("DATABASE_URL")
    if url:
        url = _corrigir_senha_url(url)
        if "sslmode" not in url:
            url += ("&" if "?" in url else "?") + "sslmode=require"
        return url

    # Permite sobrescrever via env separadas, e percent-encoda a senha.
    user = os.getenv("DB_USER", f"postgres.tltuihtisnmmabojukal")
    senha = quote_plus(os.getenv("DB_PASSWORD", "S@gui126307"))
    host = os.getenv("DB_HOST", "aws-1-us-east-2.pooler.supabase.com")
    porta = os.getenv("DB_PORT", "6543")
    nome = os.getenv("DB_NAME", "postgres")
    return f"postgresql+psycopg2://{user}:{senha}@{host}:{porta}/{nome}?sslmode=require"


DATABASE_URL = _montar_database_url()


# ------------------------------- CORS --------------------------------------
# Em produção, restrinja às URLs do seu app (ex.: https://seuapp.vercel.app)
CORS_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", "*").split(",")
                if o.strip()]
