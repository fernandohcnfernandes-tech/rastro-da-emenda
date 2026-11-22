# Relatório final — Rastro da Emenda

Documento para a equipe QKV analisar e testar o que foi entregue. Decisões detalhadas em [`docs/decisoes.md`](decisoes.md); andamento por fase no [`CLAUDE.md`](../CLAUDE.md#10-andamento).

<!-- NUMEROS -->

## 1. Entregas por fase

| Fase | Situação | O que foi entregue | Pendências |
|---|---|---|---|
| 1. Ambiente e banco | concluída | Postgres 16 em docker compose, `rastro.db.migrar` (schema + migrações 001–006), logs JSON, `/saude` | — |
| 2. Transferegov | concluída | Conector PostgREST (limit/offset, 60 req/min), cadeia ordem bancária → documento hábil → empenho → plano de ação, carga retomável | — |
| 3. Portal e IBGE | concluída | Emendas Pix e objeto declarado (arquivo oficial da CGU; API pronta para quando houver chave), municípios, população, CNPJ → IBGE (100%) | Chave do Portal (para `/emendas/documentos`) |
| 4. PNCP | concluída (ver números) | Contratos por CNPJ, contratações por UF + modalidade, varredura nacional dos últimos 14 dias, `cobertura_pncp` | — |
| 5. Querido Diário | implementada, **sem validação real** | Conector, cobertura e busca restrita a municípios ≤ 20 mil cobertos sem PNCP | API fora do ar em 22/11; regravar fixtures e rodar a busca quando voltar |
| 6. Motor e IA | concluída | Pré-filtro, IA com saída estruturada e cache, heurística sem chave, regras A1–A7, semáforo, processamento idempotente | `ANTHROPIC_API_KEY` (hoje roda a heurística) |
| 7. API | concluída | 10 endpoints, dossiê PDF, assinaturas, CPF mascarado | — |
| 8. Frontend | concluída | Início com mapa, busca, ficha, município, parlamentar, Como funciona | — |
| 9. Semanal e deploy | concluída | `atualizacao_semanal`, alertas por e-mail (log sem SMTP), Dockerfiles, `docker-compose.prod.yml`, workflow agendado | Publicar em servidor (não feito por instrução) |
| 10. Qualidade | concluída | Amostra de 30 emendas para revisão humana, README, licença, varredura de segredos | Revisão humana da amostra |
| 11. Submissão | concluída | `docs/submissao.md` (texto, roteiro do vídeo) | Gravar vídeo, URL da demo |

## 2. Passo a passo para rodar e testar do zero

```bash
git clone https://github.com/fernandohcnfernandes-tech/rastro-da-emenda && cd rastro-da-emenda
cp .env.example .env                      # opcional: ANTHROPIC_API_KEY, PORTAL_TRANSPARENCIA_API_KEY, SMTP_*
docker compose up -d db
cd backend && python3.12 -m venv .venv && source .venv/bin/activate && pip install -e ".[dev]"
python -m rastro.db.migrar
pytest -q && ruff check . && ruff format --check .        # testes não usam rede; os de API criam o banco rastro_teste

# amostra rápida (~20 min): duas UFs pequenas
python -m rastro.jobs.carga_inicial --fonte transferegov --ufs RR,AP
python -m rastro.jobs.carga_inicial --fonte ibge
python -m rastro.jobs.carga_inicial --fonte portal
python -m rastro.jobs.carga_inicial --fonte pncp --tipo contratos --ufs RR,AP
python -m rastro.motor.processar --ufs RR,AP

uvicorn rastro.api.main:app --port 8000 &
cd ../frontend && npm install && API_URL=http://localhost:8000 npm run dev   # http://localhost:3000
```

Carga nacional completa: os mesmos comandos sem `--ufs` (Transferegov ~8 min; PNCP contratos ~10 h; contratações ~16 h). Atualização semanal: `python -m rastro.jobs.atualizacao_semanal`.

## 3. Verificações manuais sugeridas

1. Revisar `docs/conferencia-amostra.md`: abrir o link de cada evidência e marcar se o status faz sentido.
2. Para uma emenda **verde**, conferir no PNCP se objeto, valor e data do contrato batem com o plano de ação.
3. Para uma emenda **vermelha**, procurar manualmente no portal da prefeitura/diário oficial: há contrato que o sistema não achou? Anotar o motivo (CNPJ diferente, contrato pequeno, publicação fora do PNCP).
4. Para uma emenda **azul**, confirmar que o município tem ≤ 20 mil habitantes e não aparece no PNCP.
5. Baixar o dossiê PDF de uma emenda de cada cor e revisar a linguagem (só "indício", nunca acusação).
6. Assinar um município no site e rodar `python -m rastro.jobs.atualizacao_semanal --sem-transferegov --sem-portal --sem-pncp --sem-querido-diario`; sem SMTP, o envio aparece no log.
7. Conferir em `/emendas/{id}` de um contrato com fornecedor pessoa física que o CPF aparece mascarado e o nome omitido.
8. Rodar o frontend em celular (layout responsivo) e o mapa filtrado por UF.

## 4. Riscos conhecidos

- **Querido Diário fora do ar:** sem ele, municípios pequenos sem PNCP ficam azuis; os cobertos não podem ser verificados até a API voltar.
- **Sem chave da Anthropic:** a correspondência usa heurística (semelhança TF-IDF + valor). Tende a perder contratos com descrição diferente do plano (falso vermelho) e pode aceitar contratos genéricos do mesmo órgão (falso verde). A ficha indica "classificação heurística".
- **Objeto declarado genérico:** muitos planos listam só áreas ("saúde, educação..."), o que reduz a precisão de qualquer correspondência; esses recebem A2.
- **Entes estaduais:** a busca no PNCP é pelo CNPJ do estado e dos executores (secretarias); contratos assinados por outros órgãos estaduais não entram.
- **Limite do PNCP (30 req/min):** cargas longas; a semanal usa varredura nacional dos últimos 14 dias.
- **Prazo:** nenhum commit depois de 30/11/2026, 23h59 (Brasília).

## 5. Decisões

Todas as decisões com data e motivo estão em [`docs/decisoes.md`](decisoes.md). Destaques: arquivo oficial da CGU no lugar da API do Portal sem chave; filtro de 10% do repasse no PNCP; CPF mascarado na ingestão; heurística sem chave de IA; semáforo conservador (cinza dentro do prazo, azul sem fonte).
