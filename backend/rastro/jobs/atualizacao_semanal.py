"""Atualização semanal (idempotente; registro em `execucao_job`).

1. Novidades do Transferegov e do Portal da Transparência (+ ligação CNPJ → IBGE de entes novos);
2. PNCP (varredura nacional dos últimos 14 dias + consulta completa dos CNPJs novos, nunca verificados),
   Tribunais de Contas e Querido Diário dos últimos 14 dias para os entes monitorados; contabilidade dos entes no
   SICONFI (fonte 706) quando o Tesouro publica um mês novo;
3. reprocessamento do motor — só emendas cujo `hash_entrada` mudou;
4. e-mail aos assinantes cujo status mudou (sem SMTP, apenas log);
5. relatório em docs/relatorios/atualizacao-semanal-AAAA-MM-DD.md.

Uso: python -m rastro.jobs.atualizacao_semanal [--sem-transferegov] [--sem-portal] [--sem-pncp] [--sem-querido-diario]
"""

from __future__ import annotations

import argparse
import time
from datetime import date, timedelta
from typing import Any

from sqlalchemy import text

from rastro import alertas
from rastro.config import config
from rastro.db.conexao import transacao
from rastro.jobs.carga_ibge_portal import RAIZ
from rastro.jobs.execucao import Execucao
from rastro.log import log

DIAS_JANELA = 14


def _status_atual() -> dict[int, str]:
    with transacao() as conn:
        return {r[0]: r[1] for r in conn.execute(text("SELECT id_plano_acao, status::text FROM avaliacao"))}


def _mudancas(antes: dict[int, str], depois: dict[int, str]) -> list[alertas.Mudanca]:
    ids = [i for i, s in depois.items() if antes.get(i) != s]
    if not ids:
        return []
    with transacao() as conn:
        linhas = conn.execute(
            text(
                "SELECT p.id_plano_acao, p.emenda_numero, p.nome_beneficiario, en.codigo_ibge, p.parlamentar_nome"
                " FROM plano_acao p LEFT JOIN ente en ON en.cnpj = p.cnpj_beneficiario"
                " WHERE p.id_plano_acao = ANY(:ids)"
            ),
            {"ids": ids},
        ).all()
    return [alertas.Mudanca(r[0], r[1], r[2], r[3], r[4], antes.get(r[0]), depois[r[0]]) for r in linhas]


def _assinaturas() -> list[alertas.Assinatura]:
    with transacao() as conn:
        return [alertas.Assinatura(*r) for r in conn.execute(text("SELECT email, tipo, chave FROM assinatura"))]


def _etapa(resumo: dict[str, Any], nome: str, funcao, *args, **kwargs) -> None:
    inicio = time.monotonic()
    try:
        resultado = funcao(*args, **kwargs)
        resumo[nome] = {"ok": True, "duracao_s": round(time.monotonic() - inicio), "resultado": resultado}
    except Exception as exc:  # uma fonte fora do ar não impede as demais etapas
        resumo[nome] = {"ok": False, "duracao_s": round(time.monotonic() - inicio), "erro": repr(exc)[:500]}
        log("atualizacao_semanal", f"{nome}:erro", erro=repr(exc)[:500])


def executar(
    transferegov: bool = True, portal: bool = True, pncp: bool = True, querido_diario: bool = True
) -> dict[str, Any]:
    from rastro.jobs import (
        carga_ibge_portal,
        carga_pncp,
        carga_querido_diario,
        carga_siconfi,
        carga_tce,
        carga_transferegov,
    )
    from rastro.motor import processar

    execucao = Execucao("atualizacao_semanal", retomar=False)
    desde = date.fromisoformat(config().data_inicio)
    resumo: dict[str, Any] = {"inicio": time.strftime("%Y-%m-%d %H:%M:%S")}
    try:
        antes = _status_atual()
        if transferegov:
            _etapa(resumo, "transferegov", carga_transferegov.carregar, desde, None, False)
            _etapa(resumo, "ibge", carga_ibge_portal.carregar_ibge)
            from rastro.jobs.carga_congresso import carregar_congresso

            _etapa(resumo, "congresso", carregar_congresso)
        if portal:
            _etapa(resumo, "portal", carga_ibge_portal.carregar_portal, desde)
        if pncp:
            _etapa(resumo, "pncp", carga_pncp.atualizar_recentes, DIAS_JANELA)
            _etapa(resumo, "pncp_cnpjs_novos", carga_pncp.carregar_contratos, desde, None, None, True)
        _etapa(resumo, "tce_rs", carga_tce.carregar_tce_rs, desde, [date.today().year])
        _etapa(resumo, "tce_pi", carga_tce.carregar_tce_pi, desde, date.today() - timedelta(days=DIAS_JANELA))
        _etapa(resumo, "tce_sp", carga_tce.carregar_tce_sp, desde, True)
        _etapa(resumo, "tce_rn", carga_tce.carregar_tce_rn, desde)
        if querido_diario:
            _etapa(resumo, "querido_diario_cobertura", carga_querido_diario.atualizar_cobertura)
            _etapa(resumo, "querido_diario", carga_querido_diario.buscar_evidencias, desde, None, DIAS_JANELA)
        _etapa(resumo, "siconfi", carga_siconfi.carregar)  # só consulta quando o Tesouro publica mês novo
        _etapa(resumo, "motor", processar.processar)
        depois = _status_atual()
        mudancas = _mudancas(antes, depois)
        mensagens = alertas.montar_mensagens(mudancas, _assinaturas(), config().url_site)
        _etapa(resumo, "alertas", alertas.enviar, mensagens)
        resumo["mudancas_de_status"] = len(mudancas)
        resumo["novas_avaliacoes"] = len(set(depois) - set(antes))
        resumo["distribuicao"] = _distribuicao()
        resumo["fim"] = time.strftime("%Y-%m-%d %H:%M:%S")
        _relatorio(resumo, mudancas)
        falhas = [k for k, v in resumo.items() if isinstance(v, dict) and v.get("ok") is False]
        execucao.concluir(resumo, status="erro" if falhas else "concluido")
        log("atualizacao_semanal", "concluida", mudancas=len(mudancas), falhas=falhas)
        return resumo
    except Exception as exc:
        execucao.falhar(repr(exc))
        raise


def _distribuicao() -> dict[str, int]:
    with transacao() as conn:
        return {r[0]: r[1] for r in conn.execute(text("SELECT status::text, count(*) FROM avaliacao GROUP BY 1"))}


def _relatorio(resumo: dict[str, Any], mudancas: list[alertas.Mudanca]) -> None:
    pasta = RAIZ / "docs" / "relatorios"
    pasta.mkdir(parents=True, exist_ok=True)
    linhas = [
        f"# Atualização semanal — {date.today():%d/%m/%Y}",
        "",
        f"Início {resumo['inicio']} · fim {resumo.get('fim')} (horário do servidor).",
        "",
        "| Etapa | Situação | Duração (s) | Resultado |",
        "|---|---|---|---|",
    ]
    for nome, v in resumo.items():
        if isinstance(v, dict) and "ok" in v:
            detalhe = v.get("resultado") if v["ok"] else v.get("erro")
            linhas.append(f"| {nome} | {'ok' if v['ok'] else 'falhou'} | {v['duracao_s']} | `{str(detalhe)[:300]}` |")
    linhas += [
        "",
        f"Mudanças de status: **{len(mudancas)}** · novas avaliações: {resumo.get('novas_avaliacoes')}",
        "",
        "Distribuição atual: " + ", ".join(f"{k}: {v}" for k, v in sorted(resumo.get("distribuicao", {}).items())),
        "",
    ]
    if mudancas:
        linhas += ["| Plano de ação | Emenda | Beneficiário | Antes | Depois |", "|---|---|---|---|---|"]
        for m in mudancas[:200]:
            linhas.append(
                f"| {m.id_plano_acao} | {m.emenda_numero} | {m.beneficiario} | {m.antes or '—'} | {m.depois} |"
            )
        if len(mudancas) > 200:
            linhas.append(f"| … | | mais {len(mudancas) - 200} mudanças | | |")
    (pasta / f"atualizacao-semanal-{date.today():%Y-%m-%d}.md").write_text("\n".join(linhas) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Atualização semanal do Rastro da Emenda")
    for fonte in ("transferegov", "portal", "pncp", "querido-diario"):
        parser.add_argument(f"--sem-{fonte}", action="store_true")
    a = parser.parse_args()
    executar(not a.sem_transferegov, not a.sem_portal, not a.sem_pncp, not a.sem_querido_diario)


if __name__ == "__main__":
    main()
