-- Rastro da Emenda — modelo de dados (PostgreSQL 16)
-- Fonte da verdade do esquema. Alterações posteriores: rastro/db/migracoes/NNN_descricao.sql

CREATE TABLE IF NOT EXISTS ente (
    cnpj                    char(14) PRIMARY KEY,
    nome                    text NOT NULL,
    uf                      char(2),
    esfera                  text CHECK (esfera IN ('estadual', 'municipal', 'outro')),
    codigo_ibge             char(7),
    populacao               integer,
    obrigado_pncp           boolean,          -- população > 20.000 ou ente estadual
    coberto_querido_diario  boolean DEFAULT false,
    atualizado_em           timestamptz DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_ente_ibge ON ente (codigo_ibge);

CREATE TABLE IF NOT EXISTS plano_acao (
    id_plano_acao           bigint PRIMARY KEY,   -- Transferegov
    codigo_plano_acao       text,
    ano_plano_acao          integer,
    situacao                text,
    emenda_ano              integer,
    emenda_numero           text,
    parlamentar_nome        text,
    cnpj_beneficiario       char(14) REFERENCES ente (cnpj),
    nome_beneficiario       text,
    uf_beneficiario         char(2),
    valor_custeio           numeric(16,2),
    valor_investimento      numeric(16,2),
    descricao_programacao   text,
    motivo_impedimento      text,
    raw                     jsonb,
    atualizado_em           timestamptz DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_plano_emenda ON plano_acao (emenda_ano, emenda_numero);
CREATE INDEX IF NOT EXISTS ix_plano_benef ON plano_acao (cnpj_beneficiario);

CREATE TABLE IF NOT EXISTS plano_trabalho (
    id                      bigint PRIMARY KEY,
    id_plano_acao           bigint REFERENCES plano_acao ON DELETE CASCADE,
    descricao               text,
    raw                     jsonb
);

CREATE TABLE IF NOT EXISTS meta (
    id                      bigint PRIMARY KEY,
    id_plano_acao           bigint REFERENCES plano_acao ON DELETE CASCADE,
    descricao               text,
    raw                     jsonb
);

CREATE TABLE IF NOT EXISTS executor (
    id                      bigint PRIMARY KEY,
    id_plano_acao           bigint REFERENCES plano_acao ON DELETE CASCADE,
    cnpj_executor           char(14),
    nome_executor           text,
    raw                     jsonb
);
CREATE INDEX IF NOT EXISTS ix_executor_cnpj ON executor (cnpj_executor);

CREATE TABLE IF NOT EXISTS pagamento (
    id                      text PRIMARY KEY,     -- id da ordem de pagamento/bancária
    id_plano_acao           bigint REFERENCES plano_acao ON DELETE CASCADE,
    data_pagamento          date,
    valor                   numeric(16,2),
    raw                     jsonb
);
CREATE INDEX IF NOT EXISTS ix_pagamento_plano ON pagamento (id_plano_acao, data_pagamento);

CREATE TABLE IF NOT EXISTS relatorio_gestao (
    id                      text PRIMARY KEY,
    id_plano_acao           bigint REFERENCES plano_acao ON DELETE CASCADE,
    situacao                text,
    valor_executado         numeric(16,2),
    valor_pendente          numeric(16,2),
    data_registro           timestamptz,
    raw                     jsonb
);

CREATE TABLE IF NOT EXISTS emenda (
    codigo_emenda           text PRIMARY KEY,     -- Portal da Transparência
    ano                     integer,
    numero                  text,
    autor                   text,
    tipo                    text,
    funcao                  text,
    subfuncao               text,
    valor_empenhado         numeric(16,2),
    valor_liquidado         numeric(16,2),
    valor_pago              numeric(16,2),
    raw                     jsonb,
    atualizado_em           timestamptz DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_emenda_num ON emenda (ano, numero);

DO $$ BEGIN
    CREATE TYPE fonte_evidencia AS ENUM ('pncp_contrato', 'pncp_contratacao', 'pncp_ata', 'querido_diario');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

CREATE TABLE IF NOT EXISTS evidencia (
    id                      bigserial PRIMARY KEY,
    fonte                   fonte_evidencia NOT NULL,
    id_externo              text NOT NULL,        -- número de controle PNCP ou id do diário + posição
    cnpj_orgao              char(14),
    codigo_ibge             char(7),
    data_publicacao         date,
    objeto                  text,
    valor                   numeric(16,2),
    modalidade              text,
    tipo_ato                text,                 -- aviso, contrato, homologacao, dispensa...
    fornecedor_documento    text,                 -- CNPJ ou CPF (CPF sempre mascarado na exibição)
    fornecedor_nome         text,
    url                     text,
    trecho                  text,                 -- trecho do diário (Querido Diário)
    raw                     jsonb,
    coletado_em             timestamptz DEFAULT now(),
    UNIQUE (fonte, id_externo)
);
CREATE INDEX IF NOT EXISTS ix_evidencia_orgao_data ON evidencia (cnpj_orgao, data_publicacao);
CREATE INDEX IF NOT EXISTS ix_evidencia_ibge_data ON evidencia (codigo_ibge, data_publicacao);

CREATE TABLE IF NOT EXISTS correspondencia (
    id_plano_acao           bigint REFERENCES plano_acao ON DELETE CASCADE,
    id_evidencia            bigint REFERENCES evidencia ON DELETE CASCADE,
    score_pre_filtro        real,
    compativel              boolean,
    confianca               real,
    resposta_ia             jsonb,
    avaliado_em             timestamptz DEFAULT now(),
    PRIMARY KEY (id_plano_acao, id_evidencia)
);

DO $$ BEGIN
    CREATE TYPE status_semaforo AS ENUM ('verde', 'amarelo', 'vermelho', 'azul', 'cinza');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

CREATE TABLE IF NOT EXISTS avaliacao (
    id_plano_acao           bigint PRIMARY KEY REFERENCES plano_acao ON DELETE CASCADE,
    status                  status_semaforo NOT NULL,
    alertas                 text[] DEFAULT '{}',  -- A1..A8
    justificativa           text,
    hash_entrada            text,                 -- evita reprocessar sem dado novo
    avaliado_em             timestamptz DEFAULT now()
);

CREATE TABLE IF NOT EXISTS cache_ia (
    hash_entrada            text PRIMARY KEY,
    modelo                  text,
    resposta                jsonb,
    criado_em               timestamptz DEFAULT now()
);

CREATE TABLE IF NOT EXISTS execucao_job (
    id                      bigserial PRIMARY KEY,
    tipo                    text NOT NULL,        -- carga_inicial:transferegov, atualizacao_semanal...
    inicio                  timestamptz DEFAULT now(),
    fim                     timestamptz,
    status                  text DEFAULT 'rodando',
    progresso               jsonb DEFAULT '{}',   -- cursor para retomada
    resumo                  jsonb
);

CREATE TABLE IF NOT EXISTS assinatura (
    id                      bigserial PRIMARY KEY,
    email                   text NOT NULL,
    tipo                    text CHECK (tipo IN ('municipio', 'parlamentar')),
    chave                   text NOT NULL,        -- código IBGE ou nome do parlamentar
    criado_em               timestamptz DEFAULT now(),
    UNIQUE (email, tipo, chave)
);
