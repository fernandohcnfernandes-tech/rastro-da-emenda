# CLAUDE.md — Rastro da Emenda

Instruções permanentes para o Claude Code neste repositório. Leia este arquivo inteiro antes de qualquer tarefa.

## 1. O que é o projeto

Sistema que fiscaliza a execução das **transferências especiais ("emendas Pix")** destinadas a estados e municípios, de **2024 até hoje**, com **atualização semanal**. Para cada emenda: coleta os dados federais, procura evidências de uso do dinheiro no ente beneficiário e classifica a execução num semáforo.

Projeto da equipe QKV para o Hack Brasil 2026, trilha **Logística & automação** (integração entre sistemas e automação de fluxo de informação). Escopo fechado: **somente emendas Pix**. Não incluir emendas com finalidade definida, de bancada ou de comissão.

## 2. Regras do hackathon que o código precisa respeitar

- **Todo o código é escrito durante o evento, neste repositório.** Não copiar código de projetos anteriores da QKV (inclusive o protótipo de busca de licitações testado com o MPPE). Biblioteca ou código aberto que já era público pode ser usado como dependência; se algum trecho for copiado, o commit deve indicar a origem.
- **Prazo:** último commit avaliado é o de **30/11/2026, 23h59**. Depois disso **nenhum commit** até a final (congelamento; commits podem desclassificar).
- **Demo** precisa ficar no ar durante a avaliação.
- **Dados pessoais:** a demo não pode expor dados pessoais reais de terceiros. Mascarar CPF de fornecedores pessoa física (ex.: `***.456.789-**`). Não exibir dados bancários além do necessário.
- **Coleta:** usar apenas APIs oficiais e respeitar limites de requisição e termos de uso. Nada de burlar captcha ou limite de plataforma.
- **Segredos:** nunca commitar `.env`, chaves de API ou senhas.

## 3. Stack

- Python 3.12, FastAPI, httpx, SQLAlchemy 2 (core) + psycopg 3, Pydantic v2, tenacity (retry), pytest.
- PostgreSQL 16 (docker compose para desenvolvimento).
- IA: SDK `anthropic`. Modelos configuráveis por variável de ambiente: `MODELO_RAPIDO` (classificação em lote) e `MODELO_ANALISE` (comparação e resumos).
- Frontend: Next.js (App Router, TypeScript), Tailwind. Mapa com dados por município (código IBGE).
- Agendamento: cron no servidor ou GitHub Actions (`.github/workflows/atualizacao-semanal.yml`).

## 4. Identidade visual (frontend e dossiê)

Marca QKV works. Cores: `#0B0F1A` (títulos, fundo escuro), `#2563EB` (destaques, links, ações), `#64748B` (textos de apoio). Fonte Arial (fallback sans-serif). Assinatura: "A próxima resposta pode transformar seu negócio."

Cores do semáforo: verde `#16A34A`, amarelo `#EAB308`, vermelho `#DC2626`, azul `#2563EB`, cinza `#94A3B8`.

## 5. Arquitetura

```
Transferegov (especiais) ─┐
Portal da Transparência ──┼─► conectores ─► PostgreSQL ─► motor de correspondência ─► avaliação (semáforo + alertas)
IBGE (população, códigos) ┘                     ▲                    │                         │
PNCP (contratos/contratações) ──────────────────┤                    ▼                         ▼
Querido Diário (só municípios ≤ 20 mil hab.) ───┘              IA (anthropic)          API FastAPI ─► Next.js / dossiê PDF / e-mail
```

- `backend/rastro/conectores/`: um módulo por fonte. Cada conector usa `base.py` (cliente HTTP com retry, limite de taxa e cache) e grava o JSON bruto (`raw jsonb`) além dos campos normalizados. `plano_acao.cnpj_beneficiario` referencia `ente`: fazer upsert do ente antes do plano de ação.
- `backend/rastro/db/schema.sql`: modelo de dados (fonte da verdade). Alterações de esquema vão para `backend/rastro/db/migracoes/NNN_descricao.sql`.
- `backend/rastro/motor/`: correspondência emenda ↔ evidência e regras de alerta.
- `backend/rastro/jobs/`: `carga_inicial.py` e `atualizacao_semanal.py`, ambos idempotentes e retomáveis (registrar progresso em `execucao_job`).
- `backend/rastro/api/`: endpoints REST para o frontend.

Detalhes das fontes: `docs/fontes-de-dados.md`. Regras e semáforo: `docs/regras-e-semaforo.md`.

## 6. Regras de negócio essenciais

1. **Chaves de ligação:** número/ano da emenda (Transferegov ↔ Portal da Transparência); CNPJ do beneficiário e do executor (Transferegov ↔ PNCP); código IBGE (IBGE ↔ Querido Diário ↔ mapa).
2. **Executor ≠ beneficiário:** a emenda pode ser executada por outro CNPJ (ex.: fundo municipal de saúde). Buscar evidências para todos os CNPJs do `executor_especial`.
3. **Janela de busca:** evidências publicadas a partir da data do primeiro pagamento (com tolerância de 30 dias antes, para licitações já em curso).
4. **Município pequeno:** população ≤ 20.000 (estimativa IBGE mais recente) → pode publicar só no diário oficial até abril de 2027 → buscar também no Querido Diário, se o município estiver coberto.
5. **Semáforo:** ver `docs/regras-e-semaforo.md`. Vermelho só quando o ente é coberto por alguma fonte e nada foi encontrado após 180 dias do pagamento. Sem fonte → azul (neutro).
6. **IA com evidência:** toda decisão da IA devolve JSON estruturado com `compativel`, `confianca` (0–1), `justificativa` e `trechos_citados`. Abaixo de 0,6 de confiança → não conta como evidência (vai para revisão). Nunca afirmar irregularidade; usar "indício" e "sem evidência encontrada".
7. **Custo da IA:** só chamar a IA para candidatos que passam no pré-filtro (CNPJ, data, faixa de valor, similaridade de texto). Cachear por `hash(entrada)`.

## 7. Convenções

- Código e nomes em português (tabelas, colunas, funções de domínio); termos técnicos em inglês quando consagrados.
- Valores monetários em `numeric(16,2)`; datas em `date`/`timestamptz`; CNPJ sempre só dígitos (14).
- Funções puras para regras de negócio, com testes em `backend/tests/`. Conectores testados com respostas gravadas (fixtures JSON), não com chamadas reais.
- Logs estruturados (JSON) com `fonte`, `etapa`, `quantidade`, `duracao_ms`.
- Commits pequenos e frequentes, mensagem em português no imperativo (`Adiciona conector PNCP`).
- Antes de cada commit: `ruff check`, `ruff format`, `pytest -q`.

## 8. Comandos

```bash
docker compose up -d db
docker compose exec -T db psql -U rastro -d rastro < backend/rastro/db/schema.sql
cd backend && source .venv/bin/activate
python -m rastro.jobs.carga_inicial --fonte transferegov --desde 2024-01-01
python -m rastro.jobs.atualizacao_semanal
uvicorn rastro.api.main:app --reload
pytest -q
```

## 9. Ordem de trabalho

Desenvolver em fases, nesta ordem: ambiente e banco → Transferegov → Portal da Transparência e IBGE → PNCP → Querido Diário → motor de correspondência e IA → API → frontend → atualização semanal, alertas e empacotamento para deploy → qualidade e documentação → textos da submissão. Ao terminar cada fase, atualizar a seção "Andamento" abaixo com data, o que foi feito e o que ficou pendente.

## 10. Andamento

- 22/11/2026: repositório criado com estrutura, documentação e esqueleto da API.
- 22/11/2026 — **Fase 1 (ambiente e banco) concluída:** Postgres 16 via docker compose (porta configurável), `python -m rastro.db.migrar` aplica `schema.sql` + migrações, conexão SQLAlchemy (`rastro/db/conexao.py`), logs JSON (`rastro/log.py`), `/saude` respondendo. Decisões em `docs/decisoes.md`.
- 22/11/2026 — **Fase 2 (Transferegov) concluída:** conector `rastro/conectores/transferegov.py` (PostgREST, limit/offset, 60 req/min), migração `001_transferegov.sql` (empenho, documento hábil, ligação do pagamento), job `python -m rastro.jobs.carga_inicial --fonte transferegov --desde 2024-01-01` idempotente e retomável (`execucao_job`). Amostra RR+AP: 855 planos de ação, 33 entes, 854 executores, 4.253 metas, 672 pagamentos (100% ligados ao plano). Carga nacional em andamento: 33.709 planos de ação, 33.237 executores (pagamentos: ver atualização abaixo).
