-- Municípios do IBGE, objeto declarado (Portal da Transparência) e documentos das emendas.

CREATE TABLE IF NOT EXISTS municipio (
    codigo_ibge             char(7) PRIMARY KEY,
    nome                    text NOT NULL,
    uf                      char(2) NOT NULL,
    nome_chave              text NOT NULL,        -- nome normalizado (sem acento, só letras e dígitos)
    populacao               integer,
    ano_populacao           integer,
    coberto_querido_diario  boolean DEFAULT false
);
CREATE INDEX IF NOT EXISTS ix_municipio_chave ON municipio (uf, nome_chave);

ALTER TABLE ente ADD COLUMN IF NOT EXISTS metodo_resolucao_ibge text;   -- exato, prefixo, aproximado, estado

ALTER TABLE plano_acao ADD COLUMN IF NOT EXISTS objeto_declarado text;   -- "Detalhamento do Objeto" (Portal)

ALTER TABLE emenda ADD COLUMN IF NOT EXISTS localidade text;
ALTER TABLE emenda ADD COLUMN IF NOT EXISTS uf text;
ALTER TABLE emenda ADD COLUMN IF NOT EXISTS origem text;                 -- api ou arquivo_cgu

CREATE TABLE IF NOT EXISTS emenda_documento (
    id                      text PRIMARY KEY,     -- código do documento no Portal
    codigo_emenda           text REFERENCES emenda ON DELETE CASCADE,
    data                    date,
    fase                    text,
    especie                 text,
    valor                   numeric(16,2),
    raw                     jsonb
);
CREATE INDEX IF NOT EXISTS ix_emenda_doc ON emenda_documento (codigo_emenda);
