"""/auth — registro público e login.

Todo cadastro novo entra como nível "usuario"; só gestores promovem.
"""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from ..auth import criar_token, hash_senha, verificar_senha
from ..database import get_db
from ..models import Usuario
from ..schemas import LoginIn, RegistroIn, TokenOut, UsuarioOut

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/registro", response_model=UsuarioOut, status_code=201)
def registrar(dados: RegistroIn, db: Session = Depends(get_db)):
    if db.query(Usuario).filter(Usuario.email == dados.email.lower()).first():
        raise HTTPException(409, "Já existe uma conta com este e-mail.")
    usuario = Usuario(
        nome=dados.nome.strip(),
        email=dados.email.lower(),
        senha_hash=hash_senha(dados.senha),
        contato=dados.contato.strip(),
        nivel="usuario",                     # regra de negócio: sempre "usuario"
    )
    db.add(usuario)
    db.commit()
    db.refresh(usuario)
    return usuario


def _autenticar(db: Session, email: str, senha: str) -> Usuario:
    usuario = db.query(Usuario).filter(Usuario.email == email.lower()).first()
    if not usuario or not verificar_senha(senha, usuario.senha_hash):
        raise HTTPException(401, "E-mail ou senha incorretos.")
    if not usuario.ativo:
        raise HTTPException(403, "Conta desativada. Procure um gestor.")
    return usuario


@router.post("/login", response_model=TokenOut)
def login(dados: LoginIn, db: Session = Depends(get_db)):
    """Login via JSON (usado pelo app Flet)."""
    usuario = _autenticar(db, dados.email, dados.senha)
    return TokenOut(access_token=criar_token(usuario.id),
                    usuario=UsuarioOut.model_validate(usuario))


@router.post("/login-form", response_model=TokenOut, include_in_schema=False)
def login_form(form: OAuth2PasswordRequestForm = Depends(),
               db: Session = Depends(get_db)):
    """Login via form (compatível com o botão Authorize do Swagger /docs)."""
    usuario = _autenticar(db, form.username, form.password)
    return TokenOut(access_token=criar_token(usuario.id),
                    usuario=UsuarioOut.model_validate(usuario))
