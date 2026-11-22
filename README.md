# Rastro da Emenda

> Segue cada real da emenda parlamentar até o contrato no município — e avisa quando o rastro some.

Projeto da equipe **QKV** para o **Hack Brasil 2026** — trilha **Logística & automação**.

O Rastro da Emenda integra os sistemas federais que registram as **transferências especiais ("emendas Pix")** com as fontes que mostram o que o estado ou município fez com o dinheiro. Para cada emenda, o sistema:

1. coleta valor, objeto, parlamentar autor, beneficiário, pagamentos e plano de trabalho (Transferegov e Portal da Transparência);
2. procura evidências de uso do recurso no **PNCP** (contratações e contratos) e, nos municípios de até 20 mil habitantes, também no **Querido Diário**;
3. usa IA para decidir se a evidência corresponde ao objeto e ao valor da emenda;
4. atribui um **semáforo de execução**, gera alertas e um dossiê com links para as fontes oficiais.

Escopo: todas as emendas Pix destinadas a estados e municípios, **de 2024 até hoje**, com **atualização semanal**.

## Equipe QKV

- Paulo Henrique Maciel Barroso (responsável pela inscrição)
- Fernando Henrique Carriço Nogueira Fernandes
- Fernando da Costa Carriço Neto

## Estrutura

```
backend/            API (FastAPI), conectores, motor de correspondência e jobs
  rastro/conectores/  Transferegov, Portal da Transparência, PNCP, Querido Diário, IBGE
  rastro/db/          schema.sql (modelo de dados)
  rastro/jobs/        carga inicial e atualização semanal
frontend/           Next.js (busca, ficha da emenda, painéis, mapa, dossiê)
docs/               fontes de dados, regras, regulamento e roteiro de desenvolvimento
CLAUDE.md           instruções para o Claude Code
```

## Como rodar (desenvolvimento)

```bash
cp .env.example .env          # preencha as chaves
docker compose up -d db       # PostgreSQL 16
docker compose exec -T db psql -U rastro -d rastro < backend/rastro/db/schema.sql
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
uvicorn rastro.api.main:app --reload
```

## Desenvolvimento com Claude Code

Abra o terminal na raiz do repositório e rode `claude`. As regras e a arquitetura do projeto estão em [`CLAUDE.md`](CLAUDE.md), que o Claude Code lê automaticamente.

## Fontes de dados

Somente fontes oficiais e abertas — ver [`docs/fontes-de-dados.md`](docs/fontes-de-dados.md).

## Aviso

O sistema aponta **indícios para apuração**, nunca acusações. Toda conclusão é acompanhada do link para o documento oficial que a sustenta.

## Licença

MIT — ver [LICENSE](LICENSE).
