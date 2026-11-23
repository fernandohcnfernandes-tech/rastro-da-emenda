-- Execução contábil das transferências especiais (fonte de recursos 706) por ente e ano, da MSC do SICONFI.
CREATE TABLE IF NOT EXISTS execucao_contabil (
    codigo_ibge     text NOT NULL,
    ano             integer NOT NULL,
    mes             integer NOT NULL,           -- mês de referência da matriz (acumulado no ano até o mês)
    sem_dados       boolean NOT NULL DEFAULT false,  -- ente não entregou a matriz do período
    receita_1706    numeric(18,2) NOT NULL DEFAULT 0,
    receita_2706    numeric(18,2) NOT NULL DEFAULT 0,
    empenhado_1706  numeric(18,2) NOT NULL DEFAULT 0,
    empenhado_2706  numeric(18,2) NOT NULL DEFAULT 0,
    liquidado_1706  numeric(18,2) NOT NULL DEFAULT 0,
    liquidado_2706  numeric(18,2) NOT NULL DEFAULT 0,
    pago_1706       numeric(18,2) NOT NULL DEFAULT 0,
    pago_2706       numeric(18,2) NOT NULL DEFAULT 0,
    rp_pago         numeric(18,2) NOT NULL DEFAULT 0,
    pago_por_funcao jsonb,
    coletado_em     timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (codigo_ibge, ano)
);
