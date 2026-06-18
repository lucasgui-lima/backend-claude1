"""Modelos do banco de dados.

Níveis de usuário ........ usuario | manutentor | gestor
Status do chamado ........ aberto | em_andamento | fechado | avaliado
Prioridade ............... baixa | media | alta | critica
"""
from datetime import datetime, timezone

from sqlalchemy import (Boolean, Column, DateTime, ForeignKey, Integer,
                        String, Text)
from sqlalchemy.orm import relationship

from .database import Base

NIVEIS = ("usuario", "manutentor", "gestor")
STATUS_CHAMADO = ("aberto", "em_andamento", "fechado", "avaliado")
PRIORIDADES = ("baixa", "media", "alta", "critica")


def agora():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(120), nullable=False)
    email = Column(String(120), unique=True, index=True, nullable=False)
    senha_hash = Column(String(255), nullable=False)
    contato = Column(String(60), default="")            # ramal / telefone
    nivel = Column(String(20), default="usuario")       # todo cadastro nasce "usuario"
    ativo = Column(Boolean, default=True)
    criado_em = Column(DateTime, default=agora)

    chamados_abertos = relationship(
        "Chamado", back_populates="solicitante",
        foreign_keys="Chamado.solicitante_id")
    chamados_atendidos = relationship(
        "Chamado", back_populates="manutentor",
        foreign_keys="Chamado.manutentor_id")


class Predio(Base):
    __tablename__ = "predios"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(120), unique=True, nullable=False)
    ativo = Column(Boolean, default=True)

    oficinas = relationship("Oficina", back_populates="predio")


class Oficina(Base):
    __tablename__ = "oficinas"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(120), nullable=False)
    predio_id = Column(Integer, ForeignKey("predios.id"), nullable=False)
    ativo = Column(Boolean, default=True)

    predio = relationship("Predio", back_populates="oficinas")
    maquinas = relationship("Maquina", back_populates="oficina")


class Maquina(Base):
    __tablename__ = "maquinas"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(120), nullable=False)
    codigo = Column(String(60), default="")             # TAG / patrimônio
    oficina_id = Column(Integer, ForeignKey("oficinas.id"), nullable=False)
    ativo = Column(Boolean, default=True)

    oficina = relationship("Oficina", back_populates="maquinas")
    chamados = relationship("Chamado", back_populates="maquina")


class Chamado(Base):
    __tablename__ = "chamados"

    id = Column(Integer, primary_key=True, index=True)
    solicitante_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    predio_id = Column(Integer, ForeignKey("predios.id"), nullable=False)
    oficina_id = Column(Integer, ForeignKey("oficinas.id"), nullable=False)
    maquina_id = Column(Integer, ForeignKey("maquinas.id"), nullable=False)
    prioridade = Column(String(20), default="media")
    descricao = Column(Text, nullable=False)
    contato_solicitante = Column(String(60), default="")

    status = Column(String(20), default="aberto", index=True)
    manutentor_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    solucao = Column(Text, default="")

    aberto_em = Column(DateTime, default=agora, index=True)
    atendido_em = Column(DateTime, nullable=True)       # quando o manutentor "puxou"
    fechado_em = Column(DateTime, nullable=True)
    avaliado_em = Column(DateTime, nullable=True)
    reaberturas = Column(Integer, default=0)

    # Avaliação do solicitante após o fechamento
    avaliacao_nota = Column(Integer, nullable=True)     # 1 a 5
    avaliacao_comentario = Column(Text, default="")
    ferramentas_retiradas = Column(Boolean, default=False)
    local_limpo = Column(Boolean, default=False)

    solicitante = relationship("Usuario", back_populates="chamados_abertos",
                               foreign_keys=[solicitante_id])
    manutentor = relationship("Usuario", back_populates="chamados_atendidos",
                              foreign_keys=[manutentor_id])
    predio = relationship("Predio")
    oficina = relationship("Oficina")
    maquina = relationship("Maquina", back_populates="chamados")


class Aviso(Base):
    """Avisos exibidos no rodapé da tela Resumo TV."""
    __tablename__ = "avisos"

    id = Column(Integer, primary_key=True, index=True)
    titulo = Column(String(120), nullable=False)
    mensagem = Column(Text, nullable=False)
    ativo = Column(Boolean, default=True)
    criado_em = Column(DateTime, default=agora)
    criado_por_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True)

    criado_por = relationship("Usuario")
