"""Autenticação e autorização.

- Senhas: PBKDF2-HMAC-SHA256 com salt aleatório (biblioteca padrão, sem deps).
- Sessão: JWT Bearer (PyJWT).
- Autorização: dependency `exigir_nivel(...)` por nível de usuário.
"""
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from .config import ACCESS_TOKEN_EXPIRE_MINUTES, ALGORITHM, SECRET_KEY
from .database import get_db
from .models import Usuario

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

_ITERACOES = 200_000


# ------------------------------ Senhas (hash) ------------------------------
def hash_senha(senha: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", senha.encode(), salt.encode(), _ITERACOES).hex()
    return f"pbkdf2${_ITERACOES}${salt}${digest}"


def verificar_senha(senha: str, armazenado: str) -> bool:
    try:
        _, iteracoes, salt, digest = armazenado.split("$")
        calc = hashlib.pbkdf2_hmac(
            "sha256", senha.encode(), salt.encode(), int(iteracoes)).hex()
        return hmac.compare_digest(calc, digest)
    except (ValueError, AttributeError):
        return False


# --------------------------------- Tokens ----------------------------------
def criar_token(usuario_id: int) -> str:
    exp = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode({"sub": str(usuario_id), "exp": exp},
                      SECRET_KEY, algorithm=ALGORITHM)


def get_usuario_atual(token: str = Depends(oauth2_scheme),
                      db: Session = Depends(get_db)) -> Usuario:
    cred_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Sessão inválida ou expirada. Faça login novamente.",
        headers={"WWW-Authenticate": "Bearer"})
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        usuario_id = int(payload.get("sub"))
    except (jwt.PyJWTError, TypeError, ValueError):
        raise cred_exc

    usuario = db.get(Usuario, usuario_id)
    if usuario is None or not usuario.ativo:
        raise cred_exc
    return usuario


def exigir_nivel(*niveis: str):
    """Dependency: libera o endpoint apenas para os níveis informados."""
    def dependency(usuario: Usuario = Depends(get_usuario_atual)) -> Usuario:
        if usuario.nivel not in niveis:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Você não tem permissão para esta ação.")
        return usuario
    return dependency
