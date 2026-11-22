# Registro de decisões

Decisões tomadas durante o desenvolvimento quando a especificação não definia o detalhe. Formato: data — decisão — motivo.

| Data | Decisão | Motivo |
|---|---|---|
| 22/11/2026 | Porta do Postgres no host configurável por `RASTRO_DB_PORTA` (padrão 5432); no servidor de desenvolvimento usa 5442, e a API usa 8010. | As portas 5432–5434, 8000 e 3000 já estavam ocupadas por outros serviços na máquina de desenvolvimento. |
| 22/11/2026 | Esquema aplicado por `python -m rastro.db.migrar`: roda `schema.sql` (idempotente) e depois cada `migracoes/NNN_*.sql` ainda não registrado em `schema_migracao`. | Atende à regra do CLAUDE.md (alterações em `migracoes/`) sem depender de ferramenta externa de migração. |
| 22/11/2026 | Chamadas ao Transferegov sempre com o User-Agent do projeto e `limit` ≤ 1000, no máximo 60 requisições/min. | A sondagem inicial com `curl` sem User-Agent e `limit` alto foi bloqueada pelo Cloudflare do gestao.gov.br; respeitamos o bloqueio e reduzimos a carga em vez de contorná-lo. |
| 22/11/2026 | Tabelas filhas do Transferegov: com até 3.000 pais, busca por `coluna=in.(...)` em lotes de 150; acima disso, varre a tabela inteira (limit/offset) e filtra localmente pelos planos ≥ 2024. | A varredura completa custa ~60 páginas por tabela, menos requisições que milhares de lotes; a amostra por UF fica rápida. |
| 22/11/2026 | Pagamento = ordem bancária; valor vem do documento hábil e o plano de ação vem do empenho (`ligar_pagamentos()`). | A tabela de ordens não traz valor nem plano de ação. |
| 22/11/2026 | Campos bancários removidos do `raw` na ingestão. | Regra de não exibir dados bancários além do necessário. |
| 22/11/2026 | **Pendência:** `PORTAL_TRANSPARENCIA_API_KEY` ausente. Sem a chave, a carga do Portal usa o arquivo oficial de dados abertos da CGU (`EmendasParlamentares.zip`, redirecionado de `portaldatransparencia.gov.br/download-de-dados/emendas-parlamentares`). O caminho pela API (`/emendas`, `/emendas/documentos/{codigo}`) está implementado e entra automaticamente quando a chave for configurada. | A API responde 401 sem chave; o arquivo é a mesma base oficial, atualizada pela CGU, e ainda traz o "Detalhamento do Objeto" de cada plano de ação. |
| 22/11/2026 | A fixture `portal/emendas_api_exemplo_swagger.json` foi montada a partir dos campos documentados no Swagger, não de resposta real. Substituir por resposta real quando houver chave. | Sem chave não é possível gravar resposta real da API. |
| 22/11/2026 | Ligação emenda ↔ plano de ação por `emenda.codigo_emenda = plano_acao.emenda_numero` (ex.: `202437940002`) e objeto declarado por `codigo_plano_acao` (`09032024-064698/2024` → `09032024-064698`). | Formatos conferidos nos dois lados; o número já embute ano + autor + sequencial. |
| 22/11/2026 | População: agregado 6579, variável 9324, período mais recente com valores (2026 na carga de 22/11). Estados recebem código `UU00000` e são sempre `obrigado_pncp`. Municípios: `obrigado_pncp = populacao > 20.000`. | Regra do CLAUDE.md (municípios ≤ 20 mil podem publicar só em diário até 2027). |
| 22/11/2026 | Resolução CNPJ → IBGE: chave do nome sem acentos/prefixos/pontuação + UF; depois tabela de sinônimos (nomes antigos: Jahu→Jaú, Presidente Juscelino→Serra Caiada etc.); por último aproximação `difflib` (corte 0,88). Entes resolvidos como município passam a ter esfera `municipal`. | 100% dos 5.359 entes resolvidos; as 21 aproximações foram conferidas manualmente. |

