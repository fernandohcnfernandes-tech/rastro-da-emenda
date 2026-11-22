# Fontes de dados

Todas as fontes são oficiais e abertas. Parâmetros marcados com **(confirmar)** devem ser conferidos no Swagger/documentação da fonte antes da implementação definitiva.

## 1. Transferegov — API Transferências Especiais (MGI)

- Base: `https://api.transferegov.gestao.gov.br/transferenciasespeciais/`
- Documentação (Swagger): `https://docs.api.transferegov.gestao.gov.br/transferenciasespeciais/`
- Tipo: PostgREST (filtros na URL no formato `?coluna=eq.valor`, paginação com `limit` e `offset`, ordenação com `order`). Sem autenticação.
- Endpoints (tabelas):

| Endpoint | Uso no projeto |
|---|---|
| `programa_especial` | Programa orçamentário |
| `plano_acao_especial` | **Núcleo:** emenda, parlamentar, beneficiário (CNPJ, nome, UF), valores de custeio e investimento, situação, impedimento |
| `plano_trabalho_especial` | Plano de trabalho declarado pelo ente |
| `meta_especial` | Metas do plano de trabalho |
| `finalidade_especial` | Finalidade |
| `executor_especial` | CNPJs executores (podem diferir do beneficiário) |
| `empenho_especial` | Empenhos |
| `documento_habil_especial` | Documentos hábeis |
| `ordem_pagamento_ordem_bancaria_especial` | Ordens de pagamento e bancárias (data e valor do repasse) |
| `historico_pagamento_especial` | Histórico de pagamentos |
| `relatorio_gestao_especial`, `relatorio_gestao_novo_especial` | Relatórios de gestão (situação, valor executado e pendente) |
| `plano_trabalho_analise_especial`, `orgao_analise_pendente_especial` | Análise do plano de trabalho |

Campos principais de `plano_acao_especial`: `id_plano_acao`, `codigo_plano_acao`, `ano_plano_acao`, `modalidade_plano_acao`, `situacao_plano_acao`, `cnpj_beneficiario_plano_acao`, `nome_beneficiario_plano_acao`, `uf_beneficiario_plano_acao`, `nome_parlamentar_emenda_plano_acao`, `ano_emenda_parlamentar_plano_acao`, `numero_emenda_parlamentar_plano_acao`, `valor_custeio_plano_acao`, `valor_investimento_plano_acao`, `motivo_impedimento_plano_acao`, `descricao_programacao_orcamentaria_plano_acao`, `id_programa`.

Exemplo: `GET .../plano_acao_especial?ano_plano_acao=gte.2024&limit=1000&offset=0`

**Confirmado em 22/11/2026 (chamadas reais, fixtures em `backend/tests/fixtures/transferegov/`):**
- Volume: 33.709 planos de ação com `ano_plano_acao >= 2024` (cabeçalho `Prefer: count=exact` devolve `content-range`).
- Ligações: `executor_especial.id_plano_acao`; `meta_especial` **não** tem `id_plano_acao` — liga por `id_executor`; `ordem_pagamento_ordem_bancaria_especial` **não** tem plano nem valor — liga por `id_dh` → `documento_habil_especial` (`valor_dh`, `id_empenho`) → `empenho_especial.id_plano_acao`. A data do repasse é `data_emissao_ob`.
- `plano_trabalho_especial` traz `classificacao_orcamentaria_pt`, `situacao_plano_trabalho` e datas de execução; o objeto declarado está em `executor_especial.objeto_executor` e `meta_especial.desc_meta`.
- `relatorio_gestao_especial` só tem situação e parecer; `relatorio_gestao_novo_especial` tem tipo (Parcial/Final), valores executado/pendente e data.
- O Cloudflare do gestao.gov.br bloqueia requisições sem User-Agent ou com `limit` muito alto: usar o User-Agent do projeto, `limit=1000` e no máximo 60 req/min.
- Campos bancários (banco, agência, conta) são removidos do `raw` antes de gravar.

## 2. Portal da Transparência — API de dados (CGU)

- Base: `https://api.portaldatransparencia.gov.br/api-de-dados`
- Chave gratuita: cadastro em `https://portaldatransparencia.gov.br/api-de-dados/cadastrar-email`. Enviar no cabeçalho `chave-api-dados` **(confirmar)**.
- Respeitar o limite de requisições por minuto informado no cadastro **(confirmar)**.

| Endpoint | Parâmetros | Uso |
|---|---|---|
| `GET /emendas` | `ano`, `codigoEmenda`, `numeroEmenda`, `nomeAutor`, `tipoEmenda`, `codigoFuncao`, `codigoSubfuncao`, `pagina` (obrigatório) | Autor, tipo, função, valores empenhado/liquidado/pago |
| `GET /emendas/documentos/{codigo}` | `pagina` | Empenhos, liquidações e pagamentos da emenda |

Filtrar pelo tipo de emenda individual de transferência especial e ligar a `plano_acao_especial` por ano + número da emenda.

**Confirmado em 22/11/2026:** sem chave a API responde `401 {"Erro na API": "Chave de API não informada!..."}`, o que confirma o cabeçalho `chave-api-dados`. Alternativa oficial sem chave: `https://portaldatransparencia.gov.br/download-de-dados/emendas-parlamentares/UNICO` → `EmendasParlamentares.zip` (CSV `;`, latin-1). `EmendasParlamentares.csv` tem uma linha por emenda (`Código da Emenda` = `numero_emenda_parlamentar_plano_acao` do Transferegov; tipo `Emenda Individual - Transferências Especiais`); `EmendasParlamentares_PlanodeTrabalhoTransferenciasEspeciais.csv` tem uma linha por plano de ação (`Plano de Ação` = `codigo_plano_acao` + `/ano`) com o **Detalhamento do Objeto**.

## 3. PNCP — API de consultas

- Base: `https://pncp.gov.br/api/consulta`
- Swagger: `https://pncp.gov.br/api/consulta/swagger-ui/index.html`
- Sem autenticação. Datas no formato `AAAAMMDD`.
- **Confirmado em 22/11/2026:** `/v1/contratos` aceita `tamanhoPagina` de 10 a 500 e período de no máximo **365 dias** (`422 Período maior que 365 dias`) → janelas anuais. `/v1/contratacoes/publicacao` aceita `tamanhoPagina` até **50**. As respostas trazem `totalRegistros`, `totalPaginas` e `paginasRestantes`. O contrato traz `numeroControlePNCP`, `numeroControlePncpCompra`, `orgaoEntidade.cnpj`, `unidadeOrgao.codigoIbge`, `objetoContrato`, `valorGlobal`, `niFornecedor`, `tipoPessoa` (PF/PJ), `dataAssinatura`, `dataPublicacaoPncp` e `emendaParlamentar` (raramente preenchido). A contratação traz `modalidadeId`/`modalidadeNome`, `objetoCompra`, `valorTotalEstimado`/`valorTotalHomologado` e `situacaoCompraNome`.
- URLs públicas: contrato `https://pncp.gov.br/app/contratos/{cnpj}/{ano}/{sequencial}`; contratação `https://pncp.gov.br/app/editais/{cnpj}/{ano}/{sequencial}`.

| Endpoint | Obrigatórios | Opcionais | Uso |
|---|---|---|---|
| `GET /v1/contratos` | `dataInicial`, `dataFinal`, `pagina` | `cnpjOrgao`, `codigoUnidadeAdministrativa`, `usuarioId`, `tamanhoPagina` | **Principal:** contratos por CNPJ do ente |
| `GET /v1/contratacoes/publicacao` | `dataInicial`, `dataFinal`, `codigoModalidadeContratacao`, `pagina` | `uf`, `codigoMunicipioIbge`, `cnpj`, `codigoUnidadeAdministrativa`, `codigoModoDisputa`, `tamanhoPagina` | Licitações e contratações diretas |
| `GET /v1/atas` | `dataInicial`, `dataFinal`, `pagina` | `cnpj` (ou `cnpjOrgao` — **confirmar**), `codigoUnidadeAdministrativa`, `tamanhoPagina` | Atas de registro de preço |

Estratégia:
- **Carga inicial:** para cada CNPJ beneficiário/executor, `/v1/contratos` de 2024-01-01 até hoje, em janelas mensais se a API limitar o intervalo **(confirmar limite de intervalo)**.
- **Contratações:** por `uf` + `codigoModalidadeContratacao` em janelas mensais, filtrando localmente pelos CNPJs monitorados.
- **Semanal:** varrer publicações dos últimos 14 dias e filtrar pelos CNPJs monitorados.

## 4. Querido Diário (Open Knowledge Brasil) — só municípios até 20 mil habitantes

- Base: `https://api.queridodiario.ok.org.br`
- Documentação: `https://docs.queridodiario.ok.org.br/en/latest/using/public-api.html`
- Limite de referência: **60 requisições por minuto**.
- `GET /cities` — lista de municípios cobertos (consultar a cada execução; a cobertura muda).
- `GET /gazettes` — busca nos diários. Parâmetros **(confirmar)**: `territory_ids` (código IBGE), `querystring` (palavras-chave), `published_since`, `published_until` (AAAA-MM-DD), `excerpt_size`, `number_of_excerpts`, `size`, `offset`.

Usar somente quando: município ≤ 20 mil habitantes **e** sem evidência no PNCP **e** coberto pelo Querido Diário. Buscar por palavras-chave do objeto da emenda combinadas com termos de ato ("extrato de contrato", "aviso de licitação", "homologação", "dispensa").

## 5. IBGE

- Municípios e códigos: `https://servicodados.ibge.gov.br/api/v1/localidades/municipios`
- População (estimativa mais recente): agregado **6579**, variável **9324** ("População residente estimada"): `/api/v3/agregados/6579/periodos/{ano}/variaveis/9324?localidades=N6[all]` (municípios) ou `N3[all]` (UFs). Confirmado em 22/11/2026; períodos sem publicação voltam vazios.
- Uso: marcar municípios com até 20 mil habitantes e ligar CNPJ ↔ código IBGE (por nome + UF do beneficiário).

## 6. Apoio (opcional)

- APIs de dados abertos da Câmara e do Senado: partido, UF e foto oficial do parlamentar.
- Cadastros CEIS/CNEP (Portal da Transparência): fornecedor sancionado (regra A8, extensão).
