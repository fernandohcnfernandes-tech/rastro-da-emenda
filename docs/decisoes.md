# Registro de decisões

Decisões tomadas durante o desenvolvimento quando a especificação não definia o detalhe. Formato: data — decisão — motivo.

| Data | Decisão | Motivo |
|---|---|---|
| 22/11/2026 | Porta do Postgres no host configurável por `RASTRO_DB_PORTA` (padrão 5432); no servidor de desenvolvimento usa 5442, e a API usa 8010. | As portas 5432–5434, 8000 e 3000 já estavam ocupadas por outros serviços na máquina de desenvolvimento. |
| 22/11/2026 | Esquema aplicado por `python -m rastro.db.migrar`: roda `schema.sql` (idempotente) e depois cada `migracoes/NNN_*.sql` ainda não registrado em `schema_migracao`. | Atende à regra do CLAUDE.md (alterações em `migracoes/`) sem depender de ferramenta externa de migração. |
| 22/11/2026 | Chamadas ao Transferegov sempre com o User-Agent do projeto e `limit` ≤ 1000, no máximo 60 requisições/min. | A sondagem inicial com `curl` sem User-Agent e `limit` alto foi bloqueada pelo Cloudflare do gestao.gov.br; respeitamos o bloqueio e reduzimos a carga em vez de contorná-lo. |
