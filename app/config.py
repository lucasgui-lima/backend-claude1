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
    m = re.match(r"^(.+://)([^:]+):([^@]+)@(.+)$", url)
    if not m:
        return url
    _scheme, _user, _senha, _resto = m.groups()
    _senha_corrigida = quote_plus(_senha)
    if _senha_corrigida == _senha:
        return url
    return f"{_scheme}{_user}:{_senha_corrigida}@{_resto}"


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
    user = os.getenv("DB_USER", "postgres")
    senha = quote_plus(os.getenv("DB_PASSWORD", "S@gui126307"))
    host = os.getenv("DB_HOST", "db.tltuihtisnmmabojukal.supabase.co")
    porta = os.getenv("DB_PORT", "5432")
    nome = os.getenv("DB_NAME", "postgres")
    return f"postgresql+psycopg2://{user}:{senha}@{host}:{porta}/{nome}?sslmode=require"


DATABASE_URL = _montar_database_url()


# ------------------------------- CORS --------------------------------------
# Em produção, restrinja às URLs do seu app (ex.: https://seuapp.vercel.app)
CORS_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", "*").split(",")
                if o.strip()]
