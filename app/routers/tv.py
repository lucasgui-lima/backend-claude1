"""/tv — dados da tela "Resumo TV" e avisos do setor.

O app na TV consulta /tv/resumo em intervalos curtos; quando o campo
`ultimo_chamado_id` aumenta, o cliente exibe o pop-up de tela inteira
por 10 segundos com os dados de `ultimo_chamado`.
"""
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from ..auth import exigir_nivel, get_usuario_atual
from ..database import get_db
from ..models import Aviso, Chamado, Usuario, agora
from ..schemas import AvisoIn, AvisoOut
from .chamados import _para_out, _query_base

router = APIRouter(prefix="/tv", tags=["tv"])

_ORDEM_PRIORIDADE = {"critica": 0, "alta": 1, "media": 2, "baixa": 3}


@router.get("/resumo")
def resumo(usuario: Usuario = Depends(get_usuario_atual),
           db: Session = Depends(get_db)):
    recentes = (_query_base(db)
                .order_by(Chamado.aberto_em.desc()).limit(8).all())

    criticos = (_query_base(db)
                .filter(Chamado.status.in_(("aberto", "em_andamento")),
                        Chamado.prioridade.in_(("critica", "alta")))
                .all())
    criticos.sort(key=lambda c: (_ORDEM_PRIORIDADE.get(c.prioridade, 9),
                                 c.aberto_em))

    ultimo = (db.query(Chamado).order_by(Chamado.id.desc()).first())

    hoje = agora().replace(hour=0, minute=0, second=0, microsecond=0)
    stats = {
        "abertos": db.query(func.count(Chamado.id))
                     .filter(Chamado.status == "aberto").scalar() or 0,
        "em_andamento": db.query(func.count(Chamado.id))
                          .filter(Chamado.status == "em_andamento").scalar() or 0,
        "fechados_hoje": db.query(func.count(Chamado.id))
                           .filter(Chamado.fechado_em >= hoje).scalar() or 0,
        "abertos_hoje": db.query(func.count(Chamado.id))
                          .filter(Chamado.aberto_em >= hoje).scalar() or 0,
    }

    avisos = (db.query(Aviso).filter(Aviso.ativo.is_(True))
              .order_by(Aviso.criado_em.desc()).limit(20).all())

    return {
        "ultimo_chamado_id": ultimo.id if ultimo else 0,
        "ultimo_chamado": _para_out(
            _query_base(db).filter(Chamado.id == ultimo.id).first()
        ).model_dump(mode="json") if ultimo else None,
        "recentes": [_para_out(c).model_dump(mode="json") for c in recentes],
        "criticos": [_para_out(c).model_dump(mode="json")
                     for c in criticos[:8]],
        "stats": stats,
        "avisos": [{"id": a.id, "titulo": a.titulo, "mensagem": a.mensagem}
                   for a in avisos],
        "agora": agora().isoformat(),
    }


# ----------------------------- Avisos (gestor) ------------------------------
@router.get("/avisos", response_model=list[AvisoOut])
def listar_avisos(_: Usuario = Depends(exigir_nivel("gestor")),
                  db: Session = Depends(get_db)):
    return db.query(Aviso).order_by(Aviso.criado_em.desc()).all()


@router.post("/avisos", response_model=AvisoOut, status_code=201)
def criar_aviso(dados: AvisoIn,
                gestor: Usuario = Depends(exigir_nivel("gestor")),
                db: Session = Depends(get_db)):
    aviso = Aviso(titulo=dados.titulo.strip(), mensagem=dados.mensagem.strip(),
                  criado_por_id=gestor.id)
    db.add(aviso)
    db.commit()
    db.refresh(aviso)
    return aviso


@router.delete("/avisos/{aviso_id}", status_code=204)
def desativar_aviso(aviso_id: int,
                    _: Usuario = Depends(exigir_nivel("gestor")),
                    db: Session = Depends(get_db)):
    aviso = db.get(Aviso, aviso_id)
    if not aviso:
        raise HTTPException(404, "Aviso não encontrado.")
    aviso.ativo = False
    db.commit()
