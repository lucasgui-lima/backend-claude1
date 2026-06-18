"""/analytics — indicadores de desempenho (tela do gestor).

Definições adotadas (manutenção corretiva):
  Downtime ........ tempo entre abertura e fechamento do chamado (máquina parada)
  MTTR ............ média do tempo de reparo = (fechado_em - atendido_em)
  MTBF ............ (horas disponíveis do período - downtime) / nº de falhas
  Disponibilidade . horas operando / horas totais do período (%)
Todos os indicadores aceitam filtros por data, manutentor, máquina,
oficina e prédio.
"""
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, joinedload

from ..auth import exigir_nivel
from ..database import get_db
from ..models import Chamado, Maquina, Oficina, Usuario, agora

router = APIRouter(prefix="/analytics", tags=["analytics"])

H = 3600.0  # segundos -> horas


def _horas(delta) -> float:
    return max(delta.total_seconds() / H, 0.0)


def _sobreposicao(c: Chamado, inicio: datetime, fim: datetime) -> float:
    """Horas de parada do chamado dentro do período analisado."""
    parada_ini = max(c.aberto_em, inicio)
    parada_fim = min(c.fechado_em or fim, fim)
    return _horas(parada_fim - parada_ini) if parada_fim > parada_ini else 0.0


def _indicadores(chamados: list[Chamado], n_maquinas: int,
                 inicio: datetime, fim: datetime) -> dict:
    periodo_h = _horas(fim - inicio)
    horas_totais = max(n_maquinas, 1) * periodo_h

    downtime = sum(_sobreposicao(c, inicio, fim) for c in chamados)
    downtime = min(downtime, horas_totais)
    falhas = len(chamados)

    fechados = [c for c in chamados if c.fechado_em]
    reparos = [_horas(c.fechado_em - (c.atendido_em or c.aberto_em))
               for c in fechados]
    atendidos = [c for c in chamados if c.atendido_em]
    respostas = [_horas(c.atendido_em - c.aberto_em) for c in atendidos]

    horas_operando = horas_totais - downtime
    mttr = sum(reparos) / len(reparos) if reparos else 0.0
    mtbf = horas_operando / falhas if falhas else horas_operando
    disponibilidade = (horas_operando / horas_totais * 100) if horas_totais else 100.0

    notas = [c.avaliacao_nota for c in chamados if c.avaliacao_nota]
    return {
        "total": falhas,
        "abertos": sum(1 for c in chamados if c.status == "aberto"),
        "em_andamento": sum(1 for c in chamados if c.status == "em_andamento"),
        "fechados": sum(1 for c in chamados
                        if c.status in ("fechado", "avaliado")),
        "mttr_horas": round(mttr, 2),
        "mtbf_horas": round(mtbf, 2),
        "disponibilidade_pct": round(disponibilidade, 2),
        "downtime_horas": round(downtime, 2),
        "tempo_resposta_horas": round(sum(respostas) / len(respostas), 2)
                                if respostas else 0.0,
        "nota_media": round(sum(notas) / len(notas), 2) if notas else None,
    }


@router.get("/indicadores")
def indicadores(inicio: Optional[datetime] = None,
                fim: Optional[datetime] = None,
                maquina_id: Optional[int] = None,
                manutentor_id: Optional[int] = None,
                oficina_id: Optional[int] = None,
                predio_id: Optional[int] = None,
                _: Usuario = Depends(exigir_nivel("gestor")),
                db: Session = Depends(get_db)):
    fim = fim or agora()
    if fim.hour == 0 and fim.minute == 0:
        fim = fim + timedelta(days=1)        # inclui o dia final por inteiro
    inicio = inicio or (fim - timedelta(days=30))

    # --- chamados do período, com filtros ---
    q = (db.query(Chamado)
         .options(joinedload(Chamado.maquina), joinedload(Chamado.manutentor))
         .filter(Chamado.aberto_em >= inicio, Chamado.aberto_em < fim))
    if maquina_id:
        q = q.filter(Chamado.maquina_id == maquina_id)
    if manutentor_id:
        q = q.filter(Chamado.manutentor_id == manutentor_id)
    if oficina_id:
        q = q.filter(Chamado.oficina_id == oficina_id)
    if predio_id:
        q = q.filter(Chamado.predio_id == predio_id)
    chamados = q.all()

    # --- máquinas no escopo (para MTBF/disponibilidade) ---
    qm = db.query(Maquina).filter(Maquina.ativo.is_(True))
    if maquina_id:
        qm = qm.filter(Maquina.id == maquina_id)
    if oficina_id:
        qm = qm.filter(Maquina.oficina_id == oficina_id)
    if predio_id:
        qm = qm.join(Oficina).filter(Oficina.predio_id == predio_id)
    maquinas = qm.order_by(Maquina.nome).all()

    geral = _indicadores(chamados, len(maquinas), inicio, fim)

    por_maquina = []
    for m in maquinas:
        cs = [c for c in chamados if c.maquina_id == m.id]
        ind = _indicadores(cs, 1, inicio, fim)
        por_maquina.append({"maquina_id": m.id, "maquina": m.nome,
                            "codigo": m.codigo, **ind})
    por_maquina.sort(key=lambda x: x["mttr_horas"], reverse=True)

    por_manutentor = []
    ids_vistos = set()
    for c in chamados:
        if c.manutentor_id and c.manutentor_id not in ids_vistos:
            ids_vistos.add(c.manutentor_id)
            cs = [x for x in chamados if x.manutentor_id == c.manutentor_id]
            ind = _indicadores(cs, len(maquinas), inicio, fim)
            por_manutentor.append({
                "manutentor_id": c.manutentor_id,
                "manutentor": c.manutentor.nome if c.manutentor else "-",
                "atendidos": len(cs),
                "fechados": ind["fechados"],
                "mttr_horas": ind["mttr_horas"],
                "tempo_resposta_horas": ind["tempo_resposta_horas"],
                "nota_media": ind["nota_media"],
            })
    por_manutentor.sort(key=lambda x: x["fechados"], reverse=True)

    por_prioridade = {p: sum(1 for c in chamados if c.prioridade == p)
                      for p in ("baixa", "media", "alta", "critica")}

    return {
        "periodo": {"inicio": inicio.isoformat(), "fim": fim.isoformat(),
                    "horas": round(_horas(fim - inicio), 1)},
        "kpis": geral,
        "por_maquina": por_maquina,
        "por_manutentor": por_manutentor,
        "por_prioridade": por_prioridade,
    }
