"""API do Rastro da Emenda."""

from __future__ import annotations

import re
from typing import Annotated, Literal

from fastapi import Depends, FastAPI, HTTPException, Query, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, field_validator
from sqlalchemy import Connection, text

from rastro import __version__
from rastro.api import consultas, dossie
from rastro.db.conexao import engine

app = FastAPI(
    title="Rastro da Emenda",
    version=__version__,
    description="Segue cada real da emenda parlamentar até o contrato no município. Aponta indícios, não acusações.",
)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["GET", "POST"], allow_headers=["*"])

Status = Literal["verde", "amarelo", "vermelho", "azul", "cinza"]
Alerta = Literal["A1", "A2", "A3", "A4", "A5", "A6", "A7"]


def conexao():
    with engine().connect() as conn:
        yield conn


Conexao = Annotated[Connection, Depends(conexao)]


@app.get("/saude")
def saude() -> dict[str, str]:
    return {"status": "ok", "versao": __version__}


@app.get("/atualizacao")
def atualizacao(conn: Conexao) -> dict:
    return consultas.ultima_atualizacao(conn)


@app.get("/emendas")
def emendas(
    conn: Conexao,
    uf: str | None = Query(None, min_length=2, max_length=2),
    municipio: str | None = Query(None, description="código IBGE ou parte do nome"),
    parlamentar: str | None = None,
    ano: int | None = None,
    status: Status | None = None,
    busca: str | None = Query(None, description="texto livre: beneficiário, município, parlamentar, objeto, número"),
    alerta: Alerta | None = None,
    ordem: Literal["repassado", "recentes", "antigas", "valor"] = "repassado",
    pagina: int = Query(1, ge=1),
    tamanho: int = Query(20, ge=1, le=100),
) -> dict:
    filtros = dict(
        uf=uf, municipio=municipio, parlamentar=parlamentar, ano=ano, status=status, busca=busca, alerta=alerta
    )
    resultado = consultas.listar_emendas(conn, pagina, tamanho, ordem, **filtros)
    resultado["resumo_status"] = consultas.resumo_status(conn, **filtros)
    return resultado


@app.get("/emendas/{id_plano_acao}")
def emenda(id_plano_acao: int, conn: Conexao) -> dict:
    ficha = consultas.ficha_emenda(conn, id_plano_acao)
    if not ficha:
        raise HTTPException(404, "Plano de ação não encontrado")
    return ficha


@app.get("/emendas/{id_plano_acao}/dossie.pdf")
def emenda_dossie(id_plano_acao: int, conn: Conexao) -> Response:
    ficha = consultas.ficha_emenda(conn, id_plano_acao)
    if not ficha:
        raise HTTPException(404, "Plano de ação não encontrado")
    return Response(
        dossie.gerar(ficha),
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="dossie-emenda-{id_plano_acao}.pdf"'},
    )


@app.get("/resumo")
def resumo(conn: Conexao) -> dict:
    return consultas.resumo(conn)


@app.get("/alertas")
def alertas(conn: Conexao) -> list:
    return consultas.alertas(conn)


@app.get("/municipios")
def municipios(
    conn: Conexao,
    busca: str | None = None,
    uf: str | None = Query(None, min_length=2, max_length=2),
    pagina: int = Query(1, ge=1),
    tamanho: int = Query(30, ge=1, le=100),
) -> dict:
    return consultas.listar_municipios(conn, busca, uf, pagina, tamanho)


@app.get("/parlamentares")
def parlamentares(
    conn: Conexao,
    busca: str | None = None,
    uf: str | None = Query(None, min_length=2, max_length=2, description="UF do parlamentar"),
    casa: Literal["camara", "senado"] | None = None,
    partido: str | None = Query(None, max_length=20),
    pagina: int = Query(1, ge=1),
    tamanho: int = Query(30, ge=1, le=100),
) -> dict:
    resultado = consultas.listar_parlamentares(conn, busca, pagina, tamanho, uf, casa, partido)
    resultado["partidos"] = consultas.partidos(conn)
    return resultado


@app.get("/municipios/{codigo_ibge}")
def municipio(codigo_ibge: str, conn: Conexao) -> dict:
    if not re.fullmatch(r"\d{7}", codigo_ibge):
        raise HTTPException(422, "Código IBGE deve ter 7 dígitos")
    info = consultas.municipio(conn, codigo_ibge)
    if not info:
        raise HTTPException(404, "Município não encontrado")
    return info


@app.get("/parlamentares/{nome}")
def parlamentar(nome: str, conn: Conexao) -> dict:
    if len(nome.strip()) < 3:
        raise HTTPException(422, "Informe ao menos 3 letras do nome")
    info = consultas.parlamentar(conn, nome.strip())
    if not info:
        raise HTTPException(404, "Parlamentar não encontrado")
    return info


@app.get("/mapa")
def mapa(conn: Conexao, uf: str | None = Query(None, min_length=2, max_length=2)) -> list:
    return consultas.mapa(conn, uf)


@app.get("/cobertura")
def cobertura(conn: Conexao) -> list:
    return consultas.cobertura(conn)


class NovaAssinatura(BaseModel):
    email: str
    tipo: Literal["municipio", "parlamentar"]
    chave: str

    @field_validator("email")
    @classmethod
    def email_valido(cls, v: str) -> str:
        v = v.strip().lower()
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", v) or len(v) > 254:
            raise ValueError("e-mail inválido")
        return v

    @field_validator("chave")
    @classmethod
    def chave_valida(cls, v: str) -> str:
        v = v.strip()
        if not v or len(v) > 200:
            raise ValueError("chave inválida")
        return v


@app.post("/assinaturas", status_code=201)
def assinar(nova: NovaAssinatura, conn: Conexao) -> dict:
    if nova.tipo == "municipio" and not re.fullmatch(r"\d{7}", nova.chave):
        raise HTTPException(422, "Para município, a chave é o código IBGE (7 dígitos)")
    conn.execute(
        text("INSERT INTO assinatura (email, tipo, chave) VALUES (:e, :t, :c) ON CONFLICT DO NOTHING"),
        {"e": nova.email, "t": nova.tipo, "c": nova.chave},
    )
    conn.commit()
    return {"ok": True, "mensagem": "Assinatura registrada. Você receberá e-mail quando o status mudar."}
