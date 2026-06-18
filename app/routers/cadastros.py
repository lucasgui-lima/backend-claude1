"""/cadastros — prédios, oficinas e máquinas.

Leitura: qualquer usuário logado (necessário para abrir chamados).
Escrita: apenas gestores.
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from sqlalchemy.orm import joinedload

from ..auth import exigir_nivel, get_usuario_atual
from ..database import get_db
from ..models import Maquina, Oficina, Predio, Usuario
from ..schemas import (MaquinaIn, MaquinaOut, OficinaIn, OficinaOut,
                       PredioIn, PredioOut)

router = APIRouter(prefix="/cadastros", tags=["cadastros"])

somente_gestor = exigir_nivel("gestor")


# --------------------------------- Prédios ---------------------------------
@router.get("/predios", response_model=list[PredioOut])
def listar_predios(_: Usuario = Depends(get_usuario_atual),
                   db: Session = Depends(get_db)):
    return (db.query(Predio).filter(Predio.ativo.is_(True))
            .order_by(Predio.nome).all())


@router.post("/predios", response_model=PredioOut, status_code=201)
def criar_predio(dados: PredioIn, _: Usuario = Depends(somente_gestor),
                 db: Session = Depends(get_db)):
    if db.query(Predio).filter(Predio.nome == dados.nome.strip()).first():
        raise HTTPException(409, "Já existe um prédio com este nome.")
    predio = Predio(nome=dados.nome.strip())
    db.add(predio)
    db.commit()
    db.refresh(predio)
    return predio


@router.delete("/predios/{predio_id}", status_code=204)
def desativar_predio(predio_id: int, _: Usuario = Depends(somente_gestor),
                     db: Session = Depends(get_db)):
    predio = db.get(Predio, predio_id)
    if not predio:
        raise HTTPException(404, "Prédio não encontrado.")
    predio.ativo = False                      # soft delete: preserva histórico
    db.commit()


# --------------------------------- Oficinas --------------------------------
@router.get("/oficinas", response_model=list[OficinaOut])
def listar_oficinas(predio_id: Optional[int] = None,
                    _: Usuario = Depends(get_usuario_atual),
                    db: Session = Depends(get_db)):
    q = (db.query(Oficina).options(joinedload(Oficina.predio))
         .filter(Oficina.ativo.is_(True)))
    if predio_id:
        q = q.filter(Oficina.predio_id == predio_id)
    oficinas = q.order_by(Oficina.nome).all()
    for o in oficinas:
        o.predio_nome = o.predio.nome if o.predio else ""
    return oficinas


@router.post("/oficinas", response_model=OficinaOut, status_code=201)
def criar_oficina(dados: OficinaIn, _: Usuario = Depends(somente_gestor),
                  db: Session = Depends(get_db)):
    if not db.get(Predio, dados.predio_id):
        raise HTTPException(404, "Prédio não encontrado.")
    oficina = Oficina(nome=dados.nome.strip(), predio_id=dados.predio_id)
    db.add(oficina)
    db.commit()
    db.refresh(oficina)
    predio = db.get(Predio, dados.predio_id)
    oficina.predio_nome = predio.nome if predio else ""
    return oficina


@router.delete("/oficinas/{oficina_id}", status_code=204)
def desativar_oficina(oficina_id: int, _: Usuario = Depends(somente_gestor),
                      db: Session = Depends(get_db)):
    oficina = db.get(Oficina, oficina_id)
    if not oficina:
        raise HTTPException(404, "Oficina não encontrada.")
    oficina.ativo = False
    db.commit()


# --------------------------------- Máquinas --------------------------------
@router.get("/maquinas", response_model=list[MaquinaOut])
def listar_maquinas(oficina_id: Optional[int] = None,
                    predio_id: Optional[int] = None,
                    _: Usuario = Depends(get_usuario_atual),
                    db: Session = Depends(get_db)):
    q = (db.query(Maquina).options(joinedload(Maquina.oficina).joinedload(Oficina.predio))
         .filter(Maquina.ativo.is_(True)))
    if oficina_id:
        q = q.filter(Maquina.oficina_id == oficina_id)
    if predio_id:
        q = q.join(Oficina).filter(Oficina.predio_id == predio_id)
    maquinas = q.order_by(Maquina.nome).all()
    for m in maquinas:
        m.oficina_nome = m.oficina.nome if m.oficina else ""
        m.predio_nome = m.oficina.predio.nome if m.oficina and m.oficina.predio else ""
    return maquinas


@router.post("/maquinas", response_model=MaquinaOut, status_code=201)
def criar_maquina(dados: MaquinaIn, _: Usuario = Depends(somente_gestor),
                  db: Session = Depends(get_db)):
    if not db.get(Oficina, dados.oficina_id):
        raise HTTPException(404, "Oficina não encontrada.")
    maquina = Maquina(nome=dados.nome.strip(), codigo=dados.codigo.strip(),
                      oficina_id=dados.oficina_id)
    db.add(maquina)
    db.commit()
    db.refresh(maquina)
    oficina = db.get(Oficina, dados.oficina_id)
    maquina.oficina_nome = oficina.nome if oficina else ""
    maquina.predio_nome = oficina.predio.nome if oficina and oficina.predio else ""
    return maquina


@router.delete("/maquinas/{maquina_id}", status_code=204)
def desativar_maquina(maquina_id: int, _: Usuario = Depends(somente_gestor),
                      db: Session = Depends(get_db)):
    maquina = db.get(Maquina, maquina_id)
    if not maquina:
        raise HTTPException(404, "Máquina não encontrada.")
    maquina.ativo = False
    db.commit()
