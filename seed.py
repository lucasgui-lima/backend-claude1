"""Popula o banco com dados de demonstração.

Executar (dentro de backend/):  python seed.py

Contas criadas:
  gestor@empresa.com      / gestor123     (gestor)
  carlos@empresa.com      / manu123       (manutentor)
  rafael@empresa.com      / manu123       (manutentor)
  ana@empresa.com         / user123       (usuário)
  joao@empresa.com        / user123       (usuário)
"""
import random
from datetime import timedelta

from app.auth import hash_senha
from app.database import Base, SessionLocal, engine
from app.models import (Aviso, Chamado, Maquina, Oficina, Predio, Usuario,
                        agora)

Base.metadata.create_all(bind=engine)
db = SessionLocal()

if db.query(Usuario).count():
    print("Banco já possui dados — seed não executado.")
    raise SystemExit(0)

# ------------------------------- Usuários -----------------------------------
gestor = Usuario(nome="Marina Gestora", email="gestor@empresa.com",
                 senha_hash=hash_senha("gestor123"), nivel="gestor",
                 contato="Ramal 1001")
manu1 = Usuario(nome="Carlos Souza", email="carlos@empresa.com",
                senha_hash=hash_senha("manu123"), nivel="manutentor",
                contato="Ramal 2001")
manu2 = Usuario(nome="Rafael Lima", email="rafael@empresa.com",
                senha_hash=hash_senha("manu123"), nivel="manutentor",
                contato="Ramal 2002")
user1 = Usuario(nome="Ana Paula", email="ana@empresa.com",
                senha_hash=hash_senha("user123"), contato="Ramal 3001")
user2 = Usuario(nome="João Pedro", email="joao@empresa.com",
                senha_hash=hash_senha("user123"), contato="Ramal 3002")
db.add_all([gestor, manu1, manu2, user1, user2])
db.flush()

# ------------------------ Prédios / oficinas / máquinas ---------------------
p1 = Predio(nome="Prédio A — Produção")
p2 = Predio(nome="Prédio B — Logística")
db.add_all([p1, p2])
db.flush()

of1 = Oficina(nome="Usinagem", predio_id=p1.id)
of2 = Oficina(nome="Montagem", predio_id=p1.id)
of3 = Oficina(nome="Expedição", predio_id=p2.id)
db.add_all([of1, of2, of3])
db.flush()

maquinas = [
    Maquina(nome="Torno CNC 01", codigo="TAG-1001", oficina_id=of1.id),
    Maquina(nome="Fresadora 02", codigo="TAG-1002", oficina_id=of1.id),
    Maquina(nome="Prensa Hidráulica", codigo="TAG-2001", oficina_id=of2.id),
    Maquina(nome="Esteira de Montagem", codigo="TAG-2002", oficina_id=of2.id),
    Maquina(nome="Empilhadeira 01", codigo="TAG-3001", oficina_id=of3.id),
    Maquina(nome="Selladora de Caixas", codigo="TAG-3002", oficina_id=of3.id),
]
db.add_all(maquinas)
db.flush()

# ------------------------------- Chamados -----------------------------------
descricoes = [
    "Máquina apresentando ruído anormal no eixo principal.",
    "Vazamento de óleo hidráulico na base do equipamento.",
    "Painel de comando não liga após queda de energia.",
    "Superaquecimento do motor durante operação contínua.",
    "Sensor de segurança da porta com falha intermitente.",
    "Correia transportadora desalinhada, travando peças.",
    "Display do CLP apagado, equipamento parado.",
    "Botão de emergência travado, impossibilitando operação.",
]
solucoes = [
    "Substituído rolamento do eixo e realizado balanceamento.",
    "Trocada vedação e reposto nível de óleo hidráulico.",
    "Religado disjuntor e substituída fonte do painel.",
    "Limpeza do sistema de ventilação e troca do sensor térmico.",
]
prioridades = ["baixa", "media", "media", "alta", "alta", "critica"]
solicitantes = [user1, user2, gestor]
manutentores = [manu1, manu2]
agora_dt = agora()

random.seed(42)
for i in range(28):
    aberto = agora_dt - timedelta(days=random.randint(0, 29),
                                  hours=random.randint(0, 23))
    maq = random.choice(maquinas)
    c = Chamado(
        solicitante_id=random.choice(solicitantes).id,
        predio_id=maq.oficina.predio_id, oficina_id=maq.oficina_id,
        maquina_id=maq.id, prioridade=random.choice(prioridades),
        descricao=random.choice(descricoes),
        contato_solicitante="Ramal 30%02d" % random.randint(1, 50),
        aberto_em=aberto,
    )
    sorte = random.random()
    if sorte < 0.62:                                   # fechado / avaliado
        c.manutentor_id = random.choice(manutentores).id
        c.atendido_em = aberto + timedelta(minutes=random.randint(10, 240))
        c.fechado_em = c.atendido_em + timedelta(
            hours=random.uniform(0.5, 10))
        c.solucao = random.choice(solucoes)
        c.status = "fechado"
        if random.random() < 0.75:                     # maioria já avaliada
            c.status = "avaliado"
            c.avaliado_em = c.fechado_em + timedelta(hours=2)
            c.avaliacao_nota = random.randint(3, 5)
            c.ferramentas_retiradas = True
            c.local_limpo = True
    elif sorte < 0.82:                                 # em andamento
        c.manutentor_id = random.choice(manutentores).id
        c.atendido_em = aberto + timedelta(minutes=random.randint(10, 240))
        c.status = "em_andamento"
    db.add(c)

# -------------------------------- Avisos ------------------------------------
db.add_all([
    Aviso(titulo="Segurança", criado_por_id=gestor.id,
          mensagem="Uso de EPI é obrigatório em todas as oficinas."),
    Aviso(titulo="Parada programada", criado_por_id=gestor.id,
          mensagem="Sábado, 08h às 12h: manutenção preventiva no Prédio A."),
    Aviso(titulo="Treinamento", criado_por_id=gestor.id,
          mensagem="NR-12 — inscrições abertas com o RH até sexta-feira."),
])

db.commit()
db.close()
print("Seed concluído! Contas de teste criadas (ver docstring do arquivo).")
