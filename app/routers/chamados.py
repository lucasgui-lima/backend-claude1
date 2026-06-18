"""/chamados — ciclo de vida completo do chamado.

Fluxo: aberto -> em_andamento (manutentor "puxa") -> fechado -> avaliado
Regras principais:
  * Solicitante NÃO abre chamado novo enquanto tiver chamado fechado sem avaliar.
  * Nível "usuario" só enxerga os próprios chamados.
  * Manutentor: puxa chamados abertos para si e finaliza os seus.
  * Gestor: edita, atribui qualquer manutentor e reabre chamados.
"""
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from ..auth import exigir_nivel, get_usuario_atual
from ..database import get_db
from ..models import Chamado, Maquina, Oficina, Predio, Usuario, agora
from ..schemas import (AvaliacaoIn, ChamadoIn, ChamadoOut, ChamadoPatch,
                       FecharIn)

router = APIRouter(prefix="/chamados", tags=["chamados"])


def _para_out(c: Chamado) -> ChamadoOut:
    return ChamadoOut(
        id=c.id, status=c.status, prioridade=c.prioridade,
        descricao=c.descricao, solucao=c.solucao or "",
        contato_solicitante=c.contato_solicitante or "",
        solicitante_id=c.solicitante_id,
        solicitante_nome=c.solicitante.nome if c.solicitante else "-",
        manutentor_id=c.manutentor_id,
        manutentor_nome=c.manutentor.nome if c.manutentor else None,
        predio_id=c.predio_id, predio_nome=c.predio.nome if c.predio else "-",
        oficina_id=c.oficina_id,
        oficina_nome=c.oficina.nome if c.oficina else "-",
        maquina_id=c.maquina_id,
        maquina_nome=c.maquina.nome if c.maquina else "-",
        aberto_em=c.aberto_em, atendido_em=c.atendido_em,
        fechado_em=c.fechado_em, avaliado_em=c.avaliado_em,
        reaberturas=c.reaberturas or 0,
        avaliacao_nota=c.avaliacao_nota,
        avaliacao_comentario=c.avaliacao_comentario or "",
        ferramentas_retiradas=bool(c.ferramentas_retiradas),
        local_limpo=bool(c.local_limpo),
    )


def _query_base(db: Session):
    return db.query(Chamado).options(
        joinedload(Chamado.solicitante), joinedload(Chamado.manutentor),
        joinedload(Chamado.predio), joinedload(Chamado.oficina),
        joinedload(Chamado.maquina))


# ------------------------------ Abrir chamado -------------------------------
@router.post("", response_model=ChamadoOut, status_code=201)
def abrir_chamado(dados: ChamadoIn,
                  usuario: Usuario = Depends(get_usuario_atual),
                  db: Session = Depends(get_db)):
    pendentes = (db.query(Chamado)
                 .filter(Chamado.solicitante_id == usuario.id,
                         Chamado.status == "fechado").count())
    if pendentes:
        raise HTTPException(
            409, f"Você possui {pendentes} chamado(s) aguardando a sua "
                 "avaliação. Avalie-os antes de abrir um novo chamado.")

    maquina = db.get(Maquina, dados.maquina_id)
    oficina = db.get(Oficina, dados.oficina_id)
    predio = db.get(Predio, dados.predio_id)
    if not (maquina and oficina and predio):
        raise HTTPException(404, "Prédio, oficina ou máquina não encontrado.")
    if maquina.oficina_id != oficina.id or oficina.predio_id != predio.id:
        raise HTTPException(400, "Máquina/oficina/prédio não conferem entre si.")

    chamado = Chamado(
        solicitante_id=usuario.id,
        predio_id=dados.predio_id, oficina_id=dados.oficina_id,
        maquina_id=dados.maquina_id, prioridade=dados.prioridade,
        descricao=dados.descricao.strip(),
        contato_solicitante=(dados.contato_solicitante or usuario.contato).strip(),
    )
    db.add(chamado)
    db.commit()
    db.refresh(chamado)
    return _para_out(chamado)


# ------------------------------ Listagens -----------------------------------
@router.get("", response_model=list[ChamadoOut])
def listar(status: Optional[str] = None,
           prioridade: Optional[str] = None,
           predio_id: Optional[int] = None,
           oficina_id: Optional[int] = None,
           maquina_id: Optional[int] = None,
           manutentor_id: Optional[int] = None,
           inicio: Optional[datetime] = None,
           fim: Optional[datetime] = None,
           busca: Optional[str] = None,
           limite: int = Query(300, le=1000),
           usuario: Usuario = Depends(get_usuario_atual),
           db: Session = Depends(get_db)):
    q = _query_base(db)

    # Escopo por nível: "usuario" só vê os próprios chamados.
    if usuario.nivel == "usuario":
        q = q.filter(Chamado.solicitante_id == usuario.id)

    if status:
        q = q.filter(Chamado.status.in_(status.split(",")))
    if prioridade:
        q = q.filter(Chamado.prioridade.in_(prioridade.split(",")))
    if predio_id:
        q = q.filter(Chamado.predio_id == predio_id)
    if oficina_id:
        q = q.filter(Chamado.oficina_id == oficina_id)
    if maquina_id:
        q = q.filter(Chamado.maquina_id == maquina_id)
    if manutentor_id:
        q = q.filter(Chamado.manutentor_id == manutentor_id)
    if inicio:
        q = q.filter(Chamado.aberto_em >= inicio)
    if fim:
        q = q.filter(Chamado.aberto_em < fim + timedelta(days=1)
                     if fim.hour == 0 and fim.minute == 0 else
                     Chamado.aberto_em <= fim)
    if busca:
        like = f"%{busca.strip()}%"
        q = (q.join(Maquina, Chamado.maquina_id == Maquina.id)
              .filter(or_(Chamado.descricao.ilike(like),
                          Maquina.nome.ilike(like))))

    return [_para_out(c) for c in
            q.order_by(Chamado.aberto_em.desc()).limit(limite).all()]


@router.get("/pendentes-avaliacao", response_model=list[ChamadoOut])
def pendentes_avaliacao(usuario: Usuario = Depends(get_usuario_atual),
                        db: Session = Depends(get_db)):
    """Chamados fechados do próprio usuário aguardando avaliação."""
    q = (_query_base(db)
         .filter(Chamado.solicitante_id == usuario.id,
                 Chamado.status == "fechado")
         .order_by(Chamado.fechado_em.asc()))
    return [_para_out(c) for c in q.all()]


@router.get("/{chamado_id}", response_model=ChamadoOut)
def detalhe(chamado_id: int,
            usuario: Usuario = Depends(get_usuario_atual),
            db: Session = Depends(get_db)):
    c = _query_base(db).filter(Chamado.id == chamado_id).first()
    if not c:
        raise HTTPException(404, "Chamado não encontrado.")
    if usuario.nivel == "usuario" and c.solicitante_id != usuario.id:
        raise HTTPException(403, "Você só pode ver os próprios chamados.")
    return _para_out(c)


# ------------------------- Ações do manutentor ------------------------------
@router.post("/{chamado_id}/atender", response_model=ChamadoOut)
def atender(chamado_id: int,
            usuario: Usuario = Depends(exigir_nivel("manutentor", "gestor")),
            db: Session = Depends(get_db)):
    """Manutentor "puxa" o chamado aberto para o próprio nome."""
    c = db.get(Chamado, chamado_id)
    if not c:
        raise HTTPException(404, "Chamado não encontrado.")
    if c.status != "aberto":
        raise HTTPException(409, "Este chamado não está mais em aberto.")
    c.manutentor_id = usuario.id
    c.status = "em_andamento"
    c.atendido_em = agora()
    db.commit()
    db.refresh(c)
    return _para_out(c)


@router.post("/{chamado_id}/fechar", response_model=ChamadoOut)
def fechar(chamado_id: int, dados: FecharIn,
           usuario: Usuario = Depends(exigir_nivel("manutentor", "gestor")),
           db: Session = Depends(get_db)):
    c = db.get(Chamado, chamado_id)
    if not c:
        raise HTTPException(404, "Chamado não encontrado.")
    if c.status not in ("aberto", "em_andamento"):
        raise HTTPException(409, "Este chamado já foi fechado.")
    if usuario.nivel == "manutentor" and c.manutentor_id != usuario.id:
        raise HTTPException(403, "Puxe o chamado para o seu nome antes de "
                                 "finalizá-lo.")
    if c.manutentor_id is None:               # gestor fechando direto
        c.manutentor_id = usuario.id
    if c.atendido_em is None:
        c.atendido_em = agora()
    c.solucao = dados.solucao.strip()
    c.status = "fechado"
    c.fechado_em = agora()
    db.commit()
    db.refresh(c)
    return _para_out(c)


# ------------------------- Avaliação do solicitante -------------------------
@router.post("/{chamado_id}/avaliar", response_model=ChamadoOut)
def avaliar(chamado_id: int, dados: AvaliacaoIn,
            usuario: Usuario = Depends(get_usuario_atual),
            db: Session = Depends(get_db)):
    c = db.get(Chamado, chamado_id)
    if not c:
        raise HTTPException(404, "Chamado não encontrado.")
    if c.solicitante_id != usuario.id:
        raise HTTPException(403, "Apenas o solicitante avalia o atendimento.")
    if c.status != "fechado":
        raise HTTPException(409, "Só é possível avaliar chamados fechados.")
    if not (dados.ferramentas_retiradas and dados.local_limpo):
        raise HTTPException(
            400, "Para concluir, confirme que todas as ferramentas foram "
                 "retiradas do local e que o local está limpo e apto para o "
                 "funcionamento de seus devidos fins.")
    c.avaliacao_nota = dados.nota
    c.avaliacao_comentario = dados.comentario.strip()
    c.ferramentas_retiradas = True
    c.local_limpo = True
    c.status = "avaliado"
    c.avaliado_em = agora()
    db.commit()
    db.refresh(c)
    return _para_out(c)


# ----------------------------- Ações do gestor ------------------------------
@router.post("/{chamado_id}/reabrir", response_model=ChamadoOut)
def reabrir(chamado_id: int,
            _: Usuario = Depends(exigir_nivel("gestor")),
            db: Session = Depends(get_db)):
    c = db.get(Chamado, chamado_id)
    if not c:
        raise HTTPException(404, "Chamado não encontrado.")
    if c.status not in ("fechado", "avaliado"):
        raise HTTPException(409, "Só é possível reabrir chamados fechados.")
    c.status = "aberto"
    c.manutentor_id = None
    c.atendido_em = None
    c.fechado_em = None
    c.avaliado_em = None
    c.solucao = ""
    c.avaliacao_nota = None
    c.avaliacao_comentario = ""
    c.ferramentas_retiradas = False
    c.local_limpo = False
    c.reaberturas = (c.reaberturas or 0) + 1
    db.commit()
    db.refresh(c)
    return _para_out(c)


@router.patch("/{chamado_id}", response_model=ChamadoOut)
def editar(chamado_id: int, dados: ChamadoPatch,
           _: Usuario = Depends(exigir_nivel("gestor")),
           db: Session = Depends(get_db)):
    """Gestor altera prioridade/descrição e atribui qualquer manutentor."""
    c = db.get(Chamado, chamado_id)
    if not c:
        raise HTTPException(404, "Chamado não encontrado.")
    if dados.prioridade:
        c.prioridade = dados.prioridade
    if dados.descricao:
        c.descricao = dados.descricao.strip()
    if dados.manutentor_id is not None:
        manutentor = db.get(Usuario, dados.manutentor_id)
        if not manutentor or manutentor.nivel not in ("manutentor", "gestor"):
            raise HTTPException(400, "Selecione um manutentor válido.")
        c.manutentor_id = manutentor.id
        if c.status == "aberto":
            c.status = "em_andamento"
            c.atendido_em = agora()
    db.commit()
    db.refresh(c)
    return _para_out(c)
