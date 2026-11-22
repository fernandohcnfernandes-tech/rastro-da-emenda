-- Campos extras de evidência do PNCP.
ALTER TABLE evidencia ADD COLUMN IF NOT EXISTS numero_controle_compra text;  -- contrato → contratação de origem
ALTER TABLE evidencia ADD COLUMN IF NOT EXISTS situacao text;
ALTER TABLE evidencia ADD COLUMN IF NOT EXISTS data_assinatura date;
ALTER TABLE evidencia ADD COLUMN IF NOT EXISTS fornecedor_pf boolean DEFAULT false;
CREATE INDEX IF NOT EXISTS ix_evidencia_compra ON evidencia (numero_controle_compra);
