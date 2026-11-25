-- Contador de acessos ao portal: uma linha por dia (horário de Brasília), sem IP nem dado pessoal.
CREATE TABLE IF NOT EXISTS acesso_diario (
    dia date PRIMARY KEY,
    visitas integer NOT NULL DEFAULT 0
);
