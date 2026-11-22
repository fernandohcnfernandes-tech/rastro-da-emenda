-- Contratos municipais informados aos Tribunais de Contas (dados abertos oficiais), começando pelo TCE-RS.
ALTER TYPE fonte_evidencia ADD VALUE IF NOT EXISTS 'tce_contrato';
ALTER TABLE ente ADD COLUMN IF NOT EXISTS coberto_tce text;   -- sigla da fonte do TCE que cobre o ente (ex.: 'TCE-RS')
