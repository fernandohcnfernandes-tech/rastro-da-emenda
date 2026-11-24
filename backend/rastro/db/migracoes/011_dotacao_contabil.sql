-- Dotação atualizada na fonte 706 (para saber se o ente orça as emendas Pix nela) e correção do empenhado de
-- dezembro, que passou a incluir o empenho inscrito em restos a pagar. Zerar o mês força a recoleta de tudo.
ALTER TABLE execucao_contabil ADD COLUMN IF NOT EXISTS dotacao_1706 numeric(18,2) NOT NULL DEFAULT 0;
ALTER TABLE execucao_contabil ADD COLUMN IF NOT EXISTS dotacao_2706 numeric(18,2) NOT NULL DEFAULT 0;
UPDATE execucao_contabil SET mes = 0;
