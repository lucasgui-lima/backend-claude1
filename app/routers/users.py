"""/usuarios — perfil próprio e administração (gestor)."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..auth import exigir_nivel, get_usuario_atual, hash_senha
from ..database import get_db
from ..models import Usuario
from ..schemas import UsuarioCreateGestor, UsuarioOut, UsuarioPatch

router = APIRouter(prefix="/usuarios", tags=["usuarios"])


@router.get("/me", response_model=UsuarioOut)
def meu_perfil(usuario: Usuario = Depends(get_usuario_atual)):
    return usuario


@router.get("", response_model=list[UsuarioOut])
def listar(nivel: Optional[str] = None,
           _: Usuario = Depends(exigir_nivel("manutentor", "gestor")),
           db: Session = Depends(get_db)):
    """Lista usuários. Manutentores usam para ver colegas; gestores para administrar.
    Filtro opcional: ?nivel=manutentor (usado no combo "atribuir a")."""
    q = db.query(Usuario).filter(Usuario.ativo.is_(True))
    if nivel:
        q = q.filter(Usuario.nivel == nivel)
    return q.order_by(Usuario.nome).all()


@router.get("/todos", response_model=list[UsuarioOut])
def listar_todos(_: Usuario = Depends(exigir_nivel("gestor")),
                 db: Session = Depends(get_db)):
    """Inclui inativos — tela de cadastros do gestor."""
    return db.query(Usuario).order_by(Usuario.nome).all()


@router.post("", response_model=UsuarioOut, status_code=201)
def criar(dados: UsuarioCreateGestor,
          _: Usuario = Depends(exigir_nivel("gestor")),
          db: Session = Depends(get_db)):
    """Gestor cria contas já com o nível desejado (ex.: manutentores)."""
    if db.query(Usuario).filter(Usuario.email == dados.email.lower()).first():
        raise HTTPException(409, "Já existe uma conta com este e-mail.")
    usuario = Usuario(nome=dados.nome.strip(), email=dados.email.lower(),
                      senha_hash=hash_senha(dados.senha),
                      contato=dados.contato.strip(), nivel=dados.nivel)
    db.add(usuario)
    db.commit()
    db.refresh(usuario)
    return usuario


@router.patch("/{usuario_id}", response_model=UsuarioOut)
def atualizar(usuario_id: int, dados: UsuarioPatch,
              gestor: Usuario = Depends(exigir_nivel("gestor")),
              db: Session = Depends(get_db)):
    """Gestor altera nível, ativo/inativo, nome e contato."""
    usuario = db.get(Usuario, usuario_id)
    if not usuario:
        raise HTTPException(404, "Usuário não encontrado.")
    if usuario.id == gestor.id and dados.nivel and dados.nivel != "gestor":
        raise HTTPException(400, "Você não pode rebaixar o próprio nível.")
    for campo, valor in dados.model_dump(exclude_none=True).items():
        setattr(usuario, campo, valor)
    db.commit()
    db.refresh(usuario)
    return usuario
