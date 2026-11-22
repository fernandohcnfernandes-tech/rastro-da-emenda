-- Parlamentares (dados abertos da Câmara e do Senado) e ligação com o nome do autor da emenda.
CREATE TABLE IF NOT EXISTS parlamentar (
    id              text PRIMARY KEY,          -- 'camara:220593' ou 'senado:5672'
    casa            text NOT NULL CHECK (casa IN ('camara', 'senado')),
    nome            text NOT NULL,             -- nome parlamentar
    nome_civil      text,
    chave_nome      text NOT NULL,
    partido         text,
    uf              char(2),
    url_foto        text,
    email           text,
    telefone        text,
    url_pagina      text,
    situacao        text,
    raw             jsonb,
    atualizado_em   timestamptz DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_parlamentar_chave ON parlamentar (chave_nome);

CREATE TABLE IF NOT EXISTS parlamentar_autor (
    nome_autor      text PRIMARY KEY,          -- plano_acao.parlamentar_nome
    id_parlamentar  text REFERENCES parlamentar ON DELETE CASCADE,
    metodo          text
);
