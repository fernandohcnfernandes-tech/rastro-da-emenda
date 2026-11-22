-- Busca sem acentos sem depender da extensão unaccent (imutável, usável em índices).
CREATE OR REPLACE FUNCTION unaccent_simples(t text) RETURNS text LANGUAGE sql IMMUTABLE PARALLEL SAFE AS $$
    SELECT translate(lower(coalesce(t, '')),
        'áàâãäéèêëíìîïóòôõöúùûüçñ',
        'aaaaaeeeeiiiiooooouuuucn')
$$;
CREATE INDEX IF NOT EXISTS ix_avaliacao_status ON avaliacao (status);
CREATE INDEX IF NOT EXISTS ix_plano_parlamentar ON plano_acao (parlamentar_nome);
CREATE INDEX IF NOT EXISTS ix_assinatura_chave ON assinatura (tipo, chave);
