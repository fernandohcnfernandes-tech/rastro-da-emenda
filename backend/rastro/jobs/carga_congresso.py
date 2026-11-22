"""Carga dos parlamentares (Câmara e Senado) e ligação com os autores das emendas."""

from __future__ import annotations

import difflib
from typing import Any

from sqlalchemy import text

from rastro.conectores import congresso
from rastro.db.conexao import transacao
from rastro.db.repositorio import upsert
from rastro.jobs.execucao import Execucao
from rastro.log import cronometro, log


def ligar_autores(autores: list[str], parlamentares: list[dict[str, Any]]) -> dict[str, tuple[str, str]]:
    """{nome do autor: (id do parlamentar, método)} — exato pela chave do nome; depois aproximado (corte 0,9).

    Em homônimos, prefere quem está em exercício e, depois, o senador (lista menor e mais estável)."""
    por_chave: dict[str, dict[str, Any]] = {}
    for p in sorted(
        parlamentares,
        key=lambda p: (p.get("situacao") != "Exercício" and p.get("situacao") != "Em exercício", p["casa"] != "senado"),
    ):
        por_chave.setdefault(p["chave_nome"], p)
    ligacoes = {}
    for autor in autores:
        k = congresso.chave(autor)
        if k in por_chave:
            ligacoes[autor] = (por_chave[k]["id"], "exato")
            continue
        proximo = difflib.get_close_matches(k, list(por_chave), n=1, cutoff=0.9)
        if proximo:
            ligacoes[autor] = (por_chave[proximo[0]]["id"], "aproximado")
    return ligacoes


def carregar_congresso() -> dict[str, Any]:
    execucao = Execucao("carga:congresso", retomar=False)
    camara, senado = congresso.cliente_camara(), congresso.cliente_senado()
    try:
        with transacao() as conn:
            autores = [
                r[0]
                for r in conn.execute(
                    text("SELECT DISTINCT parlamentar_nome FROM plano_acao WHERE parlamentar_nome IS NOT NULL")
                )
            ]
        with cronometro("congresso", "listas") as info:
            deputados = [congresso.deputado(d) for d in congresso.deputados(camara)]
            atuais = {s["IdentificacaoParlamentar"]["CodigoParlamentar"]: s for s in congresso.senadores_atuais(senado)}
            legislatura = congresso.senadores_legislatura(senado)
            senadores = {}
            for s in legislatura:
                codigo = s["IdentificacaoParlamentar"]["CodigoParlamentar"]
                senadores[codigo] = congresso.senador(atuais.get(codigo, s))
            for codigo, s in atuais.items():
                senadores.setdefault(codigo, congresso.senador(s))
            todos = deputados + list(senadores.values())
            info["quantidade"] = len(todos)
        ligacoes = ligar_autores(autores, todos)
        # Detalhe (gabinete, e-mail, telefone) só dos deputados autores de emendas.
        ids_autores = {i for i, _ in ligacoes.values()}
        with cronometro("congresso", "detalhes_camara") as info:
            detalhados = 0
            for i, d in enumerate(deputados):
                if d["id"] not in ids_autores:
                    continue
                try:
                    detalhe = (camara.get(f"/deputados/{d['id'].split(':')[1]}") or {}).get("dados")
                    deputados[i] = congresso.deputado({"id": d["id"].split(":")[1], **d["raw"]}, detalhe)
                    deputados[i]["chave_nome"] = d["chave_nome"]
                    detalhados += 1
                except Exception as exc:
                    log("congresso", "detalhe:erro", id=d["id"], erro=repr(exc)[:200])
            info["quantidade"] = detalhados
        with transacao() as conn:
            upsert(conn, "parlamentar", deputados + list(senadores.values()), ("id",))
            conn.execute(text("DELETE FROM parlamentar_autor"))
            upsert(
                conn,
                "parlamentar_autor",
                [{"nome_autor": a, "id_parlamentar": i, "metodo": m} for a, (i, m) in ligacoes.items()],
                ("nome_autor",),
                jsonb=(),
            )
        resumo = {
            "parlamentares": len(todos),
            "autores": len(autores),
            "autores_ligados": len(ligacoes),
            "sem_ligacao": sorted(set(autores) - set(ligacoes))[:50],
        }
        execucao.concluir(resumo)
        log("congresso", "carga:concluida", **{k: v for k, v in resumo.items() if k != "sem_ligacao"})
        return resumo
    except Exception as exc:
        execucao.falhar(repr(exc))
        raise
    finally:
        camara.fechar()
        senado.fechar()
