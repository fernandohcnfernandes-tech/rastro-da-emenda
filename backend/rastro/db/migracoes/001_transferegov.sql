-- Ajustes do modelo após conferir a API Transferências Especiais (22/11/2026).
-- Pagamento liga-se ao plano de ação por ordem bancária → documento hábil → empenho.

ALTER TABLE plano_acao ADD COLUMN IF NOT EXISTS codigo_parlamentar text;
ALTER TABLE plano_acao ADD COLUMN IF NOT EXISTS areas_politicas text;
ALTER TABLE plano_acao ADD COLUMN IF NOT EXISTS id_programa integer;

ALTER TABLE plano_trabalho ADD COLUMN IF NOT EXISTS situacao text;
ALTER TABLE plano_trabalho ADD COLUMN IF NOT EXISTS data_inicio_execucao date;
ALTER TABLE plano_trabalho ADD COLUMN IF NOT EXISTS data_fim_execucao date;

ALTER TABLE executor ADD COLUMN IF NOT EXISTS objeto text;
ALTER TABLE executor ADD COLUMN IF NOT EXISTS valor_custeio numeric(16,2);
ALTER TABLE executor ADD COLUMN IF NOT EXISTS valor_investimento numeric(16,2);

ALTER TABLE meta ADD COLUMN IF NOT EXISTS id_executor bigint;
ALTER TABLE meta ADD COLUMN IF NOT EXISTS nome text;
ALTER TABLE meta ADD COLUMN IF NOT EXISTS valor_custeio numeric(16,2);
ALTER TABLE meta ADD COLUMN IF NOT EXISTS valor_investimento numeric(16,2);

CREATE TABLE IF NOT EXISTS empenho (
    id_empenho              bigint PRIMARY KEY,
    id_plano_acao           bigint REFERENCES plano_acao ON DELETE CASCADE,
    numero                  text,
    situacao                text,
    data_emissao            date,
    valor                   numeric(16,2),
    raw                     jsonb
);
CREATE INDEX IF NOT EXISTS ix_empenho_plano ON empenho (id_plano_acao);

CREATE TABLE IF NOT EXISTS documento_habil (
    id_dh                   bigint PRIMARY KEY,
    id_empenho              bigint REFERENCES empenho ON DELETE CASCADE,
    numero                  text,
    situacao                text,
    data_emissao            date,
    valor                   numeric(16,2),
    raw                     jsonb
);
CREATE INDEX IF NOT EXISTS ix_dh_empenho ON documento_habil (id_empenho);

ALTER TABLE pagamento ADD COLUMN IF NOT EXISTS id_dh bigint;
ALTER TABLE pagamento ADD COLUMN IF NOT EXISTS numero_ordem_bancaria text;
ALTER TABLE pagamento ADD COLUMN IF NOT EXISTS situacao text;
CREATE INDEX IF NOT EXISTS ix_pagamento_dh ON pagamento (id_dh);

ALTER TABLE relatorio_gestao ADD COLUMN IF NOT EXISTS tipo text;
ALTER TABLE relatorio_gestao ADD COLUMN IF NOT EXISTS parecer text;
CREATE INDEX IF NOT EXISTS ix_relatorio_plano ON relatorio_gestao (id_plano_acao);
CREATE INDEX IF NOT EXISTS ix_meta_plano ON meta (id_plano_acao);
CREATE INDEX IF NOT EXISTS ix_executor_plano ON executor (id_plano_acao);
CREATE INDEX IF NOT EXISTS ix_pt_plano ON plano_trabalho (id_plano_acao);
