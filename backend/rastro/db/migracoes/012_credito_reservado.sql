-- Crédito indisponível na fonte 706 (PCASP 6.2.2.1.2): pré-empenhado (.02) e bloqueado/outras indisponibilidades
-- (.01 e .99), separados. Zerar o mês força a recoleta de tudo.
ALTER TABLE execucao_contabil ADD COLUMN IF NOT EXISTS preempenhado_1706 numeric(18,2) NOT NULL DEFAULT 0;
ALTER TABLE execucao_contabil ADD COLUMN IF NOT EXISTS preempenhado_2706 numeric(18,2) NOT NULL DEFAULT 0;
ALTER TABLE execucao_contabil ADD COLUMN IF NOT EXISTS bloqueado_1706 numeric(18,2) NOT NULL DEFAULT 0;
ALTER TABLE execucao_contabil ADD COLUMN IF NOT EXISTS bloqueado_2706 numeric(18,2) NOT NULL DEFAULT 0;
UPDATE execucao_contabil SET mes = 0;
