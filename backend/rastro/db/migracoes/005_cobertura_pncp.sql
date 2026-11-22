-- Quantos registros cada CNPJ monitorado tem no PNCP (inclusive os descartados pelo filtro de valor).
CREATE TABLE IF NOT EXISTS cobertura_pncp (
    cnpj                    char(14) PRIMARY KEY,
    contratos_encontrados   integer NOT NULL DEFAULT 0,
    contratos_gravados      integer NOT NULL DEFAULT 0,
    verificado_em           timestamptz DEFAULT now()
);
ALTER TABLE correspondencia ADD COLUMN IF NOT EXISTS metodo text;   -- ia, cache ou heuristica
ALTER TABLE avaliacao ADD COLUMN IF NOT EXISTS detalhes jsonb;      -- valores usados na decisão
