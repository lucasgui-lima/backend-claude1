"""Schemas (Pydantic v2) de entrada e saída da API."""
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field

Nivel = Literal["usuario", "manutentor", "gestor"]
Prioridade = Literal["baixa", "media", "alta", "critica"]
Status = Literal["aberto", "em_andamento", "fechado", "avaliado"]


# ----------------------------- Auth / Usuários -----------------------------
class RegistroIn(BaseModel):
    nome: str = Field(min_length=3, max_length=120)
    email: EmailStr
    senha: str = Field(min_length=6, max_length=72)
    contato: str = ""


class LoginIn(BaseModel):
    email: EmailStr
    senha: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    usuario: "UsuarioOut"


class UsuarioOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    nome: str
    email: EmailStr
    contato: str
    nivel: Nivel
    ativo: bool


class UsuarioCreateGestor(RegistroIn):
    """Gestor pode criar usuário já definindo o nível (ex.: manutentor)."""
    nivel: Nivel = "usuario"


class UsuarioPatch(BaseModel):
    nivel: Optional[Nivel] = None
    ativo: Optional[bool] = None
    contato: Optional[str] = None
    nome: Optional[str] = None


# --------------------------------- Cadastros -------------------------------
class PredioIn(BaseModel):
    nome: str = Field(min_length=2, max_length=120)


class PredioOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    nome: str
    ativo: bool


class OficinaIn(BaseModel):
    nome: str = Field(min_length=2, max_length=120)
    predio_id: int


class OficinaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    nome: str
    predio_id: int
    predio_nome: str = ""
    ativo: bool


class MaquinaIn(BaseModel):
    nome: str = Field(min_length=2, max_length=120)
    codigo: str = ""
    oficina_id: int


class MaquinaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    nome: str
    codigo: str
    oficina_id: int
    oficina_nome: str = ""
    predio_nome: str = ""
    ativo: bool


# --------------------------------- Chamados --------------------------------
class ChamadoIn(BaseModel):
    predio_id: int
    oficina_id: int
    maquina_id: int
    prioridade: Prioridade = "media"
    descricao: str = Field(min_length=5)
    contato_solicitante: str = ""


class ChamadoPatch(BaseModel):
    """Edições do gestor: prioridade, manutentor, descrição."""
    prioridade: Optional[Prioridade] = None
    manutentor_id: Optional[int] = None
    descricao: Optional[str] = None


class FecharIn(BaseModel):
    solucao: str = Field(min_length=3)


class AvaliacaoIn(BaseModel):
    nota: int = Field(ge=1, le=5)
    comentario: str = ""
    ferramentas_retiradas: bool
    local_limpo: bool


class ChamadoOut(BaseModel):
    id: int
    status: Status
    prioridade: Prioridade
    descricao: str
    solucao: str
    contato_solicitante: str
    solicitante_id: int
    solicitante_nome: str
    manutentor_id: Optional[int]
    manutentor_nome: Optional[str]
    predio_id: int
    predio_nome: str
    oficina_id: int
    oficina_nome: str
    maquina_id: int
    maquina_nome: str
    aberto_em: datetime
    atendido_em: Optional[datetime]
    fechado_em: Optional[datetime]
    avaliado_em: Optional[datetime]
    reaberturas: int
    avaliacao_nota: Optional[int]
    avaliacao_comentario: str
    ferramentas_retiradas: bool
    local_limpo: bool


# ---------------------------------- Avisos ---------------------------------
class AvisoIn(BaseModel):
    titulo: str = Field(min_length=2, max_length=120)
    mensagem: str = Field(min_length=2)


class AvisoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    titulo: str
    mensagem: str
    ativo: bool
    criado_em: datetime


TokenOut.model_rebuild()
