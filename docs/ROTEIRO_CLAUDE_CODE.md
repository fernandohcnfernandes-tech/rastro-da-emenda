# Roteiro de desenvolvimento com Claude Code

Cada etapa tem um prompt pronto para colar no Claude Code. Rode as etapas em ordem. Ao fim de cada uma: revise o diff, rode os testes, faça commit e peça ao Claude Code para atualizar a seção "Andamento" do `CLAUDE.md`.

Prazo final: **30/11/2026, 23h59** (último commit avaliado). Meta interna: submeter até as 18h de 30/11.

## Preparação (uma vez)

1. Instale: Git, Python 3.12, Node 20+, Docker e o Claude Code (`npm install -g @anthropic-ai/claude-code`).
2. Clone e entre no projeto:
   ```bash
   git clone https://github.com/fernandohcnfernandes-tech/rastro-da-emenda.git
   cd rastro-da-emenda
   cp .env.example .env
   ```
3. Preencha no `.env`: `ANTHROPIC_API_KEY`, `PORTAL_TRANSPARENCIA_API_KEY` (cadastro gratuito no Portal da Transparência) e, se for usar, as variáveis de SMTP.
4. Rode `claude` na raiz do repositório. O Claude Code lê o `CLAUDE.md` automaticamente.

---

## Etapa 1 — Ambiente e banco (22/11)

```
Leia CLAUDE.md e docs/fontes-de-dados.md. Prepare o ambiente de desenvolvimento:
1) suba o Postgres com docker compose e aplique backend/rastro/db/schema.sql;
2) crie o venv, instale o backend com as dependências de dev e confirme que `uvicorn rastro.api.main:app` responde em /saude;
3) configure ruff e pytest e crie um teste simples para /saude.
Não implemente conectores ainda. Ao final, me mostre os comandos que funcionaram e atualize o Andamento no CLAUDE.md.
```

## Etapa 2 — Conector Transferegov (22–23/11)

```
Implemente backend/rastro/conectores/transferegov.py usando o cliente base (rastro/conectores/base.py).
- Baixe, com paginação limit/offset, as tabelas plano_acao_especial (ano_plano_acao >= 2024), plano_trabalho_especial, meta_especial, executor_especial, empenho_especial, ordem_pagamento_ordem_bancaria_especial, relatorio_gestao_especial e relatorio_gestao_novo_especial, filtrando pelos planos de ação de 2024 em diante.
- Antes de escrever o parser, faça uma chamada real com limit=2 em cada tabela para confirmar os nomes dos campos e salve as respostas como fixtures em backend/tests/fixtures/transferegov/.
- Grave no Postgres com upsert (campos normalizados + raw jsonb), normalizando CNPJ para 14 dígitos.
- Crie o comando `python -m rastro.jobs.carga_inicial --fonte transferegov --desde 2024-01-01`, idempotente e retomável, registrando progresso em execucao_job.
- Testes com as fixtures (sem rede).
Rode a carga completa em segundo plano e me informe quantos planos de ação, pagamentos e executores foram carregados.
```

## Etapa 3 — Portal da Transparência e IBGE (23/11)

```
Implemente os conectores portal_transparencia.py e ibge.py.
- Portal: GET /emendas por ano (2024, 2025, 2026) com paginação, cabeçalho de chave a partir de PORTAL_TRANSPARENCIA_API_KEY, respeitando o limite de requisições. Confirme no Swagger o nome do cabeçalho e o valor de tipoEmenda das transferências especiais. Ligue cada emenda ao plano de ação por ano + número da emenda e grave em emenda. Para as emendas ligadas, busque /emendas/documentos/{codigo}.
- IBGE: carregue municípios (código, nome, UF) e a estimativa populacional mais recente; preencha a tabela ente com codigo_ibge, populacao e obrigado_pncp (população > 20.000 ou ente estadual).
- Resolva o código IBGE de cada CNPJ beneficiário por nome + UF (normalizando acentos e prefixos como "MUNICIPIO DE", "PREFEITURA MUNICIPAL DE", "FUNDO MUNICIPAL DE SAUDE DE"). Gere um relatório dos CNPJs não resolvidos.
Testes com fixtures. Ao final, me dê a porcentagem de planos de ação com emenda ligada e com código IBGE resolvido.
```

## Etapa 4 — Conector PNCP (24/11)

```
Implemente backend/rastro/conectores/pncp.py (base https://pncp.gov.br/api/consulta).
- /v1/contratos por cnpjOrgao para cada CNPJ beneficiário e executor, de 2024-01-01 até hoje, tamanhoPagina=500. Descubra com uma chamada real se a API limita o intervalo de datas; se limitar, use janelas mensais.
- /v1/contratacoes/publicacao por uf + codigoModalidadeContratacao em janelas mensais, filtrando localmente pelos CNPJs monitorados.
- Grave em evidencia (fonte = pncp_contrato | pncp_contratacao) com objeto, valor, fornecedor, modalidade, data e URL pública do PNCP.
- Fila com controle de taxa, retry exponencial e retomada (execucao_job). Rode em segundo plano e mostre a estimativa de tempo da carga completa.
Testes com fixtures gravadas de respostas reais.
```

## Etapa 5 — Conector Querido Diário (24/11)

```
Implemente backend/rastro/conectores/querido_diario.py.
- Consulte /cities e marque ente.coberto_querido_diario.
- Só para planos de ação de municípios com populacao <= 20000, cobertos pelo Querido Diário e sem evidência no PNCP: busque /gazettes com territory_ids, published_since (data do 1º pagamento − 30 dias), e querystring montada a partir de palavras-chave do objeto/plano de trabalho combinadas com "extrato de contrato", "aviso de licitação", "homologação" e "dispensa". Confirme os nomes dos parâmetros no Swagger.
- Limite de 60 requisições por minuto, cache por consulta.
- Grave os trechos encontrados em evidencia (fonte = querido_diario) com URL do diário e trecho.
Testes com fixtures.
```

## Etapa 6 — Motor de correspondência e IA (25/11)

```
Implemente backend/rastro/motor/ conforme docs/regras-e-semaforo.md:
1) pre_filtro.py: candidatos por CNPJ, data, faixa de valor e similaridade de texto (TF-IDF com scikit-learn; top 5 por emenda);
2) ia.py: cliente anthropic que recebe emenda + candidato e devolve o JSON do contrato definido no documento (use saída estruturada e valide com Pydantic). MODELO_RAPIDO para classificar trechos de diário, MODELO_ANALISE para comparar objeto. Cache por hash da entrada na tabela cache_ia;
3) regras.py: regras A1 a A7 como funções puras;
4) semaforo.py: decide o status e grava em avaliacao com justificativa e alertas.
Testes unitários para regras e semáforo cobrindo todos os status, incluindo o azul. Rode o motor em lote para todo o país e me mostre a distribuição de status por UF.
```

## Etapa 7 — API (25–26/11)

```
Crie os endpoints em backend/rastro/api/:
- GET /emendas (filtros: uf, municipio_ibge, parlamentar, ano, status; paginação)
- GET /emendas/{id_plano_acao} (ficha completa: dados, linha do tempo, pagamentos, evidências com links, alertas, justificativa)
- GET /municipios/{codigo_ibge} e GET /parlamentares/{nome} (resumos)
- GET /mapa (status agregado por município para o mapa)
- GET /cobertura (cobertura de fontes por UF)
- GET /emendas/{id}/dossie.pdf (dossiê em PDF com a identidade QKV works)
- POST /assinaturas (e-mail + município ou parlamentar)
Mascarar CPF de pessoa física em todas as respostas. Testes de API com dados de exemplo.
```

## Etapa 8 — Frontend (26/11)

```
Crie o frontend em frontend/ com Next.js (App Router, TypeScript, Tailwind), seguindo a identidade visual do CLAUDE.md:
- Página inicial: busca por município, UF ou parlamentar e mapa do Brasil colorido pelo semáforo;
- Página do município e do parlamentar: totais recebidos, % com evidência, lista de emendas com status;
- Ficha da emenda: linha do tempo (indicação → plano de trabalho → pagamento → licitação → contrato), evidências com links para PNCP/diário, alertas e botão do dossiê;
- Página "Como funciona" com fontes, limitações (municípios ≤ 20 mil e cobertura do Querido Diário) e aviso de que o sistema aponta indícios;
- Data da última atualização visível no rodapé.
```

## Etapa 9 — Atualização semanal, alertas e deploy (27/11)

```
1) Implemente rastro/jobs/atualizacao_semanal.py: novidades do Transferegov e do Portal da Transparência; PNCP dos últimos 14 dias para os CNPJs monitorados; Querido Diário dos últimos 14 dias para os municípios pequenos cobertos; reprocessamento só das emendas com dado novo; registro em execucao_job; e-mail para assinantes cujos status mudaram.
2) Ative o agendamento semanal (segunda-feira, madrugada) no servidor ou no .github/workflows/atualizacao-semanal.yml.
3) Prepare o deploy da API, do banco e do frontend (Docker) e um banco pré-carregado para a demo. Escreva no README o passo a passo de deploy.
Rode a atualização semanal uma vez e me mostre o relatório.
```

## Etapa 10 — Qualidade e documentação (28/11)

```
1) Sorteie 30 emendas de estados diferentes e gere um relatório de conferência (status, evidência, link) para revisão humana; ajuste limiares e prompts conforme os erros encontrados.
2) Revise o README (o que é, como rodar, arquitetura, fontes, limitações, equipe), confirme a licença MIT e remova qualquer segredo do histórico.
3) Rode ruff e pytest e corrija tudo.
```

## Etapa 11 — Submissão (29–30/11)

```
Escreva em docs/submissao.md: nome, frase de apresentação, descrição (até 1.500 caracteres), trilha, links (repositório e demo) e o roteiro do vídeo de 3 minutos (0:00–0:20 problema; 0:20–0:40 o que existe e onde para; 0:40–2:15 demo com mapa, ficha de uma emenda verde e de uma vermelha, dossiê; 2:15–2:45 arquitetura; 2:45–3:00 impacto).
```

Depois de submeter: **não fazer mais commits** até a final.
