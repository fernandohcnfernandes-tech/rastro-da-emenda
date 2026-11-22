"""Querido Diário: cobertura (/cities) e busca de atos (/gazettes) em municípios pequenos sem PNCP."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from sqlalchemy import text

from rastro.conectores import querido_diario as qd
from rastro.config import config
from rastro.db.conexao import transacao
from rastro.db.repositorio import upsert
from rastro.jobs.carga_ibge_portal import PASTA_DADOS
from rastro.jobs.execucao import Execucao
from rastro.log import cronometro, log

TOLERANCIA_DIAS = 30

SQL_CANDIDATOS = """
WITH pagos AS (
    SELECT id_plano_acao, min(data_pagamento) AS primeiro_pagamento
    FROM pagamento WHERE id_plano_acao IS NOT NULL AND data_pagamento IS NOT NULL GROUP BY id_plano_acao
), cnpjs AS (
    SELECT p.id_plano_acao, p.cnpj_beneficiario AS cnpj FROM plano_acao p
    UNION SELECT e.id_plano_acao, e.cnpj_executor FROM executor e
)
SELECT p.id_plano_acao, p.cnpj_beneficiario, en.codigo_ibge, pg.primeiro_pagamento,
       concat_ws(' ', p.objeto_declarado,
                 (SELECT string_agg(e.objeto, ' ') FROM executor e WHERE e.id_plano_acao = p.id_plano_acao),
                 (SELECT string_agg(m.descricao, ' ') FROM meta m WHERE m.id_plano_acao = p.id_plano_acao)
       ) AS objeto
FROM plano_acao p
JOIN pagos pg USING (id_plano_acao)
JOIN ente en ON en.cnpj = p.cnpj_beneficiario
WHERE p.ano_plano_acao >= :ano
  AND en.esfera = 'municipal' AND en.populacao <= :limite AND en.coberto_querido_diario
  AND (:todas OR p.uf_beneficiario = ANY(:ufs))
  AND NOT EXISTS (
      SELECT 1 FROM evidencia ev JOIN cnpjs c ON c.cnpj = ev.cnpj_orgao
      WHERE c.id_plano_acao = p.id_plano_acao AND ev.fonte <> 'querido_diario'
        AND ev.data_publicacao >= pg.primeiro_pagamento - :tolerancia)
ORDER BY p.uf_beneficiario, p.id_plano_acao
"""


def _cities(cli) -> Any:
    """GET /cities sem parâmetros devolve os 5.570 municípios com o nível de cobertura (confirmado em 22/11/2026)."""
    return cli.get("/cities")


def atualizar_cobertura() -> dict[str, int]:
    cli = qd.cliente()
    try:
        with cronometro("querido_diario", "cobertura") as info:
            cobertos = qd.territorios_cobertos(_cities(cli))
            with transacao() as conn:
                conn.execute(
                    text("UPDATE municipio SET coberto_querido_diario = (codigo_ibge = ANY(:c))"),
                    {"c": list(cobertos)},
                )
                conn.execute(
                    text("UPDATE ente SET coberto_querido_diario = coalesce(codigo_ibge = ANY(:c), false)"),
                    {"c": list(cobertos)},
                )
                entes = conn.execute(
                    text("SELECT count(*) FROM ente WHERE coberto_querido_diario AND populacao <= :l"),
                    {"l": config().limite_populacao_pequeno},
                ).scalar_one()
            info.update(quantidade=len(cobertos), entes_pequenos_cobertos=entes)
        return {"territorios_cobertos": len(cobertos), "entes_pequenos_cobertos": entes}
    finally:
        cli.fechar()


def candidatos(desde: date, ufs: list[str] | None = None) -> list[Any]:
    params = {
        "ano": desde.year,
        "limite": config().limite_populacao_pequeno,
        "todas": not ufs,
        "ufs": [u.upper() for u in (ufs or [])],
        "tolerancia": TOLERANCIA_DIAS,
    }
    with transacao() as conn:
        return conn.execute(text(SQL_CANDIDATOS), params).all()


def buscar_evidencias(desde: date, ufs: list[str] | None = None, janela_dias: int | None = None) -> dict[str, Any]:
    """Busca nos diários. `janela_dias` limita a busca aos últimos N dias (atualização semanal)."""
    tipo = "querido_diario:busca" + (f":{','.join(sorted(ufs))}" if ufs else "")
    execucao = Execucao(tipo, retomar=janela_dias is None)
    feitos: set[int] = set(execucao.progresso.get("feitos", []))
    cli = qd.cliente(cache_dir=PASTA_DADOS / "cache" / "querido_diario")
    total = {"planos": 0, "trechos": 0, "erros": 0}
    try:
        for i, c in enumerate(candidatos(desde, ufs), 1):
            if c.id_plano_acao in feitos:
                continue
            inicio = c.primeiro_pagamento - timedelta(days=TOLERANCIA_DIAS)
            if janela_dias:
                inicio = max(inicio, date.today() - timedelta(days=janela_dias))
            consulta = qd.montar_consulta(qd.palavras_chave(c.objeto))
            try:
                resposta = qd.buscar(cli, c.codigo_ibge, consulta, inicio)
            except Exception as exc:
                total["erros"] += 1
                log("querido_diario", "busca:erro", plano=c.id_plano_acao, erro=repr(exc)[:300])
                continue
            evid = qd.evidencias_de_diarios(resposta, c.cnpj_beneficiario)
            if evid:
                with transacao() as conn:
                    upsert(
                        conn,
                        "evidencia",
                        {(e["fonte"], e["id_externo"]): e for e in evid}.values(),
                        ("fonte", "id_externo"),
                    )
            feitos.add(c.id_plano_acao)
            total["planos"] += 1
            total["trechos"] += len(evid)
            if i % 20 == 0:
                execucao.salvar(feitos=sorted(feitos))
                log("querido_diario", "busca:progresso", **total)
        execucao.salvar(feitos=sorted(feitos))
        execucao.concluir(total, status="concluido" if not total["erros"] else "erro")
        log("querido_diario", "busca:concluida", **total)
        return total
    except Exception as exc:
        execucao.falhar(repr(exc))
        raise
    finally:
        cli.fechar()
