"""Dados abertos da Câmara dos Deputados e do Senado Federal (sem chave).

- Câmara: https://dadosabertos.camara.leg.br/api/v2/deputados?idLegislatura=57 (paginado) e /deputados/{id}
- Senado: https://legis.senado.leg.br/dadosabertos/senador/lista/atual e /senador/lista/legislatura/57
Confirmado em 22/11/2026. O detalhe da Câmara traz CPF e data de nascimento: esses campos **não** são gravados.
"""

from __future__ import annotations

import re
from typing import Any

from rastro.conectores.base import ClienteHttp
from rastro.util import sem_acentos

LEGISLATURA = 57
CAMPOS_PESSOAIS = {"cpf", "dataNascimento", "dataFalecimento", "municipioNascimento", "ufNascimento", "sexo"}


def chave(nome: str | None) -> str:
    """Nome normalizado para casar autor da emenda e parlamentar ("Dep. Fulano" → "FULANO")."""
    texto = sem_acentos(nome or "").upper()
    texto = re.sub(r"^(DEP|DEPUTADO|DEPUTADA|SEN|SENADOR|SENADORA)\.?\s+", "", texto.strip())
    return re.sub(r"[^A-Z0-9]", "", texto)


def cliente_camara() -> ClienteHttp:
    return ClienteHttp("https://dadosabertos.camara.leg.br/api/v2", por_minuto=60, timeout=60)


def cliente_senado() -> ClienteHttp:
    return ClienteHttp("https://legis.senado.leg.br/dadosabertos", por_minuto=60, timeout=60)


def deputados(cli: ClienteHttp, legislatura: int = LEGISLATURA) -> list[dict[str, Any]]:
    resultado, pagina = [], 1
    while True:
        resposta = cli.get("/deputados", params={"idLegislatura": legislatura, "itens": 100, "pagina": pagina}) or {}
        resultado += resposta.get("dados") or []
        if not any(link.get("rel") == "next" for link in resposta.get("links") or []):
            return resultado
        pagina += 1


def deputado(r: dict[str, Any], detalhe: dict[str, Any] | None = None) -> dict[str, Any]:
    status = (detalhe or {}).get("ultimoStatus") or {}
    gabinete = status.get("gabinete") or {}
    bruto = {k: v for k, v in (detalhe or r).items() if k not in CAMPOS_PESSOAIS}
    return {
        "id": f"camara:{r['id']}",
        "casa": "camara",
        "nome": status.get("nomeEleitoral") or r.get("nome"),
        "nome_civil": (detalhe or {}).get("nomeCivil"),
        "chave_nome": chave(r.get("nome")),
        "partido": status.get("siglaPartido") or r.get("siglaPartido"),
        "uf": status.get("siglaUf") or r.get("siglaUf"),
        "url_foto": (status.get("urlFoto") or r.get("urlFoto") or "").replace("http://", "https://") or None,
        "email": gabinete.get("email") or r.get("email"),
        "telefone": gabinete.get("telefone"),
        "url_pagina": f"https://www.camara.leg.br/deputados/{r['id']}",
        "situacao": status.get("situacao"),
        "raw": bruto,
    }


def _lista(valor: Any) -> list:
    return valor if isinstance(valor, list) else [valor] if valor else []


def senadores_atuais(cli: ClienteHttp) -> list[dict[str, Any]]:
    resposta = cli.get("/senador/lista/atual") or {}
    return _lista(resposta.get("ListaParlamentarEmExercicio", {}).get("Parlamentares", {}).get("Parlamentar"))


def senadores_legislatura(cli: ClienteHttp, legislatura: int = LEGISLATURA) -> list[dict[str, Any]]:
    resposta = cli.get(f"/senador/lista/legislatura/{legislatura}") or {}
    return _lista(resposta.get("ListaParlamentarLegislatura", {}).get("Parlamentares", {}).get("Parlamentar"))


def senador(r: dict[str, Any]) -> dict[str, Any]:
    ident = r.get("IdentificacaoParlamentar") or {}
    codigo = ident.get("CodigoParlamentar")
    mandatos = _lista((r.get("Mandatos") or {}).get("Mandato")) or _lista(r.get("Mandato"))
    uf = ident.get("UfParlamentar") or next((m.get("UfParlamentar") for m in mandatos if m.get("UfParlamentar")), None)
    telefones = _lista((ident.get("Telefones") or {}).get("Telefone"))
    foto = (
        ident.get("UrlFotoParlamentar") or f"https://www.senado.leg.br/senadores/img/fotos-oficiais/senador{codigo}.jpg"
    )
    return {
        "id": f"senado:{codigo}",
        "casa": "senado",
        "nome": ident.get("NomeParlamentar"),
        "nome_civil": ident.get("NomeCompletoParlamentar"),
        "chave_nome": chave(ident.get("NomeParlamentar")),
        "partido": ident.get("SiglaPartidoParlamentar"),
        "uf": uf,
        "url_foto": foto.replace("http://", "https://"),
        "email": ident.get("EmailParlamentar"),
        "telefone": f"(61) {telefones[0]['NumeroTelefone']}"
        if telefones and telefones[0].get("NumeroTelefone")
        else None,
        "url_pagina": (
            ident.get("UrlPaginaParlamentar") or f"https://www25.senado.leg.br/web/senadores/senador/-/perfil/{codigo}"
        ).replace("http://", "https://"),
        "situacao": "Em exercício" if ident.get("UrlFotoParlamentar") else None,
        "raw": r,
    }
