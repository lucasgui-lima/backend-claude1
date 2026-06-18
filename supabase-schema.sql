-- ============================================================
-- Gestão de Manutenção — Schema para Supabase (PostgreSQL)
-- ============================================================
-- Execute este SQL no SQL Editor do Supabase:
--   1. Acesse https://supabase.com → Seu projeto → SQL Editor
--   2. Cole e execute
-- ============================================================

-- Tabela de usuários
CREATE TABLE IF NOT EXISTS usuarios (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(120) NOT NULL,
    email VARCHAR(120) UNIQUE NOT NULL,
    senha_hash VARCHAR(255) NOT NULL,
    contato VARCHAR(60) DEFAULT '',
    nivel VARCHAR(20) DEFAULT 'usuario',
    ativo BOOLEAN DEFAULT TRUE,
    criado_em TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_usuarios_email ON usuarios(email);

-- Tabela de prédios
CREATE TABLE IF NOT EXISTS predios (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(120) UNIQUE NOT NULL,
    ativo BOOLEAN DEFAULT TRUE
);

-- Tabela de oficinas
CREATE TABLE IF NOT EXISTS oficinas (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(120) NOT NULL,
    predio_id INTEGER NOT NULL REFERENCES predios(id),
    ativo BOOLEAN DEFAULT TRUE
);

-- Tabela de máquinas
CREATE TABLE IF NOT EXISTS maquinas (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(120) NOT NULL,
    codigo VARCHAR(60) DEFAULT '',
    oficina_id INTEGER NOT NULL REFERENCES oficinas(id),
    ativo BOOLEAN DEFAULT TRUE
);

CREATE INDEX IF NOT EXISTS idx_maquinas_oficina ON maquinas(oficina_id);

-- Tabela de chamados
CREATE TABLE IF NOT EXISTS chamados (
    id SERIAL PRIMARY KEY,
    solicitante_id INTEGER NOT NULL REFERENCES usuarios(id),
    predio_id INTEGER NOT NULL REFERENCES predios(id),
    oficina_id INTEGER NOT NULL REFERENCES oficinas(id),
    maquina_id INTEGER NOT NULL REFERENCES maquinas(id),
    prioridade VARCHAR(20) DEFAULT 'media',
    descricao TEXT NOT NULL,
    contato_solicitante VARCHAR(60) DEFAULT '',
    status VARCHAR(20) DEFAULT 'aberto',
    manutentor_id INTEGER REFERENCES usuarios(id),
    solucao TEXT DEFAULT '',
    aberto_em TIMESTAMP DEFAULT NOW(),
    atendido_em TIMESTAMP,
    fechado_em TIMESTAMP,
    avaliado_em TIMESTAMP,
    reaberturas INTEGER DEFAULT 0,
    avaliacao_nota INTEGER,
    avaliacao_comentario TEXT DEFAULT '',
    ferramentas_retiradas BOOLEAN DEFAULT FALSE,
    local_limpo BOOLEAN DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS idx_chamados_status ON chamados(status);
CREATE INDEX IF NOT EXISTS idx_chamados_aberto_em ON chamados(aberto_em);
CREATE INDEX IF NOT EXISTS idx_chamados_solicitante ON chamados(solicitante_id);
CREATE INDEX IF NOT EXISTS idx_chamados_manutentor ON chamados(manutentor_id);

-- Tabela de avisos (TV)
CREATE TABLE IF NOT EXISTS avisos (
    id SERIAL PRIMARY KEY,
    titulo VARCHAR(120) NOT NULL,
    mensagem TEXT NOT NULL,
    ativo BOOLEAN DEFAULT TRUE,
    criado_em TIMESTAMP DEFAULT NOW(),
    criado_por_id INTEGER REFERENCES usuarios(id)
);

-- ============================================================
-- Dados de demonstração (opcional)
-- ============================================================
-- Execute o seed.py após conectar o backend ao Supabase:
--   cd backend && python seed.py
-- ============================================================
