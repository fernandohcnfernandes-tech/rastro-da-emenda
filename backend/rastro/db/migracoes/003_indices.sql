CREATE INDEX IF NOT EXISTS ix_plano_codigo ON plano_acao (codigo_plano_acao);
CREATE INDEX IF NOT EXISTS ix_plano_ano_uf ON plano_acao (ano_plano_acao, uf_beneficiario);
