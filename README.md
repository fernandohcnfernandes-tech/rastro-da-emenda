# Rastro da Emenda

> Segue cada real da emenda parlamentar até o contrato no município — e avisa quando o rastro some.

Projeto da equipe **QKV** para o **Hack Brasil 2026** — trilha **Logística & automação**.

**Demo:** https://rastrodaemenda.com.br

O Rastro da Emenda integra os sistemas federais que registram as **transferências especiais ("emendas Pix")** com as fontes que mostram o que o município, o estado ou o Distrito Federal fez com o dinheiro. Para cada plano de ação, de **2024 até hoje** e com **atualização semanal**, o sistema:

1. coleta valor, objeto, parlamentar, beneficiário, executores, pagamentos, plano de trabalho e relatórios de gestão (Transferegov e Portal da Transparência);
2. procura evidências de uso do recurso no **PNCP** (contratos e contratações do ente e dos executores), nos contratos informados aos **Tribunais de Contas** com dados abertos (RS, SP, PI e RN) e, para qualquer ente coberto sem evidência no PNCP, nos diários oficiais via **Querido Diário**;
3. usa IA (**Claude Haiku 5.5**; sem chave, uma regra transparente) para decidir se a evidência corresponde ao objeto e ao valor da emenda — documentos que citam o número da emenda entram sempre como candidatos;
4. atribui um **semáforo de execução** (verde, amarelo, laranja, vermelho, azul, cinza), gera alertas A1–A9, um **dossiê em PDF** com links para as fontes oficiais (opcionalmente com parecer da IA) e **alertas por e-mail** para quem assina um município ou parlamentar;
5. oferece, na ficha de cada emenda, um **assistente de análise** (**Claude Sonnet 5.5**) que consulta o banco do projeto, responde sobre a emenda e os contratos e redige trechos para o dossiê, sempre em linguagem de indício e citando as fontes;
6. tem o menu **Pergunte à IA** ([/assistente](https://rastrodaemenda.com.br/assistente)): um consultor (**Claude Sonnet 5.5**) que responde perguntas em linguagem natural sobre todos os dados do portal — panorama, rankings por UF, município, parlamentar, partido ou beneficiário, buscas e fichas —, com tabelas e links para as fichas usadas.

> **Aviso:** o sistema aponta **indícios para apuração**, nunca acusações. "Sem evidência encontrada nas fontes consultadas" significa apenas que nada foi localizado nas bases públicas.

## Arquitetura

```
Transferegov (especiais) ─┐
Portal da Transparência ──┼─► conectores ─► PostgreSQL ─► motor de correspondência ─► avaliação (semáforo + alertas)
IBGE (população, códigos) ┘                     ▲                    │                         │
PNCP (contratos/contratações) ──────────────────┤                    ▼                         ▼
Tribunais de Contas (RS, SP, PI, RN) ───────────┤        IA: Claude Haiku 5.5      API FastAPI ─► Next.js / dossiê PDF / e-mail
Querido Diário (entes cobertos) ────────────────┤                                         │
Câmara e Senado (perfil dos autores) ───────────┘                     assistente e Pergunte à IA (Claude Sonnet 5.5)
```

```
backend/                 Python 3.12 · FastAPI · SQLAlchemy core · psycopg 3 · Pydantic v2
  rastro/conectores/     transferegov, portal, ibge, pncp, querido_diario, tce_rs/sp/pi/rn, congresso (cliente HTTP com retry, limite de taxa e cache)
  rastro/db/             schema.sql + migracoes/NNN_*.sql (aplicados por `python -m rastro.db.migrar`)
  rastro/motor/          pre_filtro (CNPJ, data, valor, TF-IDF) · ia (saída estruturada + cache) · regras A1–A9 · semaforo · processar
  rastro/jobs/           carga_inicial (por fonte, retomável) · atualizacao_semanal
  rastro/agente/         assistente da ficha e consultor do portal (laço de ferramentas somente leitura sobre o banco)
  rastro/api/            endpoints REST, dossiê PDF, assistente e consultor
  tests/                 pytest com fixtures reais gravadas (nenhum teste acessa a rede)
frontend/                Next.js 16 (App Router, TypeScript, Tailwind): visão geral, mapa (municípios e estados), fichas com assistente, municípios, estados e DF, parlamentares, alertas, cobertura das fontes, Pergunte à IA
docs/                    fontes de dados, regras e semáforo, decisões, relatórios, submissão e relatório final
```

Detalhes: [`docs/fontes-de-dados.md`](docs/fontes-de-dados.md) · [`docs/regras-e-semaforo.md`](docs/regras-e-semaforo.md) · [`docs/decisoes.md`](docs/decisoes.md) · [`docs/RELATORIO_FINAL.md`](docs/RELATORIO_FINAL.md).

## Como rodar (desenvolvimento)

Pré-requisitos: Docker, Python 3.12, Node 22.

```bash
cp .env.example .env                # preencha as chaves (opcionais: ANTHROPIC_API_KEY, PORTAL_TRANSPARENCIA_API_KEY, SMTP_*)
                                    # IA no motor: MOTOR_USA_IA=true e MODELO_MOTOR=claude-haiku-5-5
                                    # chave sem workspace: ANTHROPIC_WORKSPACE_ID=<id do workspace>
docker compose up -d db             # PostgreSQL 16 (porta em RASTRO_DB_PORTA, padrão 5432)
cd backend
python3.12 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
python -m rastro.db.migrar          # schema + migrações

# Cargas (idempotentes e retomáveis; progresso em execucao_job)
python -m rastro.jobs.carga_inicial --fonte transferegov --desde 2024-01-01   # ~8 min
python -m rastro.jobs.carga_inicial --fonte ibge
python -m rastro.jobs.carga_inicial --fonte portal                            # arquivo oficial da CGU se não houver chave
python -m rastro.jobs.carga_inicial --fonte pncp --tipo contratos             # longa: ~10 h a 30 req/min
python -m rastro.jobs.carga_inicial --fonte pncp --tipo contratacoes          # longa
python -m rastro.jobs.carga_inicial --fonte querido_diario
python -m rastro.jobs.carga_inicial --fonte tce                               # RS, PI, SP e RN (ou --ufs RS,PI)
python -m rastro.motor.processar                                              # semáforo e alertas
# Amostra rápida: acrescente --ufs RR,AP às cargas e ao motor

uvicorn rastro.api.main:app --reload --port 8000
pytest -q && ruff check . && ruff format --check .

cd ../frontend
npm install
API_URL=http://localhost:8000 npm run dev      # http://localhost:3000
```

Atualização semanal: `python -m rastro.jobs.atualizacao_semanal` (gera `docs/relatorios/atualizacao-semanal-AAAA-MM-DD.md`).

## Deploy (produção)

O repositório traz `backend/Dockerfile`, `frontend/Dockerfile` e `docker-compose.prod.yml` (banco, API e frontend). A API aplica as migrações ao iniciar; o frontend lê `API_URL` em tempo de execução.

```bash
# no servidor, na raiz do repositório
cp .env.example .env && echo "POSTGRES_PASSWORD=<senha forte>" >> .env   # e as chaves desejadas; URL_SITE=https://seu-dominio
docker compose -f docker-compose.prod.yml up -d --build                    # API em 127.0.0.1:8000, site em 127.0.0.1:3000
# cargas (uma vez) num contêiner de job próprio — não use "exec api": um novo deploy recria a API e interrompe o job
J="docker compose -f docker-compose.prod.yml --env-file .env run --rm atualizacao python -m"
$J rastro.jobs.carga_inicial --fonte transferegov
$J rastro.jobs.carga_inicial --fonte ibge
$J rastro.jobs.carga_inicial --fonte portal
$J rastro.jobs.carga_inicial --fonte congresso
$J rastro.jobs.carga_inicial --fonte tce
docker compose -f docker-compose.prod.yml --env-file .env run -d --rm atualizacao python -m rastro.jobs.carga_inicial --fonte pncp --tipo contratos
$J rastro.motor.processar
```

Alternativa às cargas longas: restaurar um dump do banco de desenvolvimento (`pg_dump -Fc` → `pg_restore` no contêiner `db`).

Publique as portas 3000 (site) e, se quiser a API pública, 8000 atrás de um proxy reverso com HTTPS (Caddy ou Nginx).

**Atualização semanal** — escolha uma das opções:

- cron no servidor (recomendado): `0 6 * * 1 cd /caminho/rastro-da-emenda && docker compose -f docker-compose.prod.yml run --rm atualizacao >> /var/log/rastro-semanal.log 2>&1` (segunda-feira, 03h de Brasília);
- GitHub Actions (`.github/workflows/atualizacao-semanal.yml`, já agendado): cadastre o segredo `DATABASE_URL` apontando para um banco acessível pela internet; sem ele, o workflow apenas registra que não há banco configurado.

## Fontes de dados

Somente APIs e bases **oficiais e abertas**, respeitando limites de requisição e termos de uso:

| Fonte | Uso | Limite adotado |
|---|---|---|
| [Transferegov — Transferências Especiais](https://docs.api.transferegov.gestao.gov.br/transferenciasespeciais/) | planos de ação, executores, metas, empenhos, ordens bancárias, relatórios de gestão | 60 req/min |
| [Portal da Transparência](https://portaldatransparencia.gov.br/api-de-dados) (API ou [arquivo de dados abertos](https://portaldatransparencia.gov.br/download-de-dados/emendas-parlamentares)) | emendas, autor, objeto declarado | 80 req/min |
| [IBGE](https://servicodados.ibge.gov.br/api/docs) | municípios, população estimada, malha do mapa | 60 req/min |
| [PNCP](https://pncp.gov.br/api/consulta/swagger-ui/index.html) | contratos e contratações | 30 req/min (medido) |
| [Querido Diário](https://queridodiario.ok.org.br) | diários oficiais dos entes cobertos (≈ 480, incluindo o DF) | 60 req/min, com cache |
| [Câmara dos Deputados](https://dadosabertos.camara.leg.br/swagger/api.html) e [Senado Federal](https://legis.senado.leg.br/dadosabertos/docs/) | partido, UF, foto e contato institucional dos autores | 60 req/min |
| Tribunais de Contas — [TCE-RS](https://dados.tce.rs.gov.br), [TCE-SP](https://transparencia.tce.sp.gov.br), [TCE-PI](https://www.tcepi.tc.br/portaldacidadania/dados-abertos), [TCE-RN](https://apidadosabertos.tce.rn.gov.br) | contratos que municípios e órgãos estaduais informam ao tribunal | arquivos anuais/semestrais; APIs a 30 req/min |

## Limitações

- Municípios com até 20 mil habitantes podem publicar contratações só no diário oficial até abril de 2027; neles a verificação depende do Querido Diário e dos Tribunais de Contas com dados abertos, que cobrem parte dos municípios. Sem nenhuma fonte, o status é **azul** (neutro), nunca vermelho.
- Enquanto o ente não foi consultado no PNCP, a emenda fica **cinza** ("verificação em andamento"); documentos com confiança entre 45% e 59% deixam a emenda **em revisão** (laranja), para conferência humana.
- **Vermelho exige sinal contrário à execução**, não só ausência de documento: contabilidade do ente no SICONFI com menos de 30% das emendas Pix empenhadas (A9) ou relatório de gestão final abaixo de 70% (A8). Sem documento e sem sinal contrário, a emenda fica **azul** (sem evidência localizada). Motivo: nas emendas que o próprio ente declara executadas, a busca automática encontra o contrato em só ~22% (ver `docs/regras-e-semaforo.md`).
- A emenda Pix entra no caixa do ente sem conta específica: a ligação com contratos é inferida por CNPJ (beneficiário e executores), data, valor e semelhança de objeto.
- Contratos abaixo de 10% do repasse não entram na análise; execuções pulverizadas em muitos contratos pequenos tendem a aparecer como amarelo ou vermelho.
- Sem `ANTHROPIC_API_KEY` (ou com `MOTOR_USA_IA=false`), a comparação usa uma heurística transparente (indicada na ficha como "classificação heurística") e o assistente fica indisponível. A IA pode errar: o sistema sempre mostra o documento oficial para conferência.
- Dados pessoais: CPF de fornecedor pessoa física é mascarado (`***.456.789-**`) e o nome é omitido já na ingestão.

## Equipe QKV

- Paulo Henrique Maciel Barroso (responsável pela inscrição)
- Fernando Henrique Carriço Nogueira Fernandes
- Fernando da Costa Carriço Neto

## Licença

MIT — ver [LICENSE](LICENSE).
