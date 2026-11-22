"""Carga inicial por fonte.

Exemplos:
    python -m rastro.jobs.carga_inicial --fonte transferegov --desde 2024-01-01
    python -m rastro.jobs.carga_inicial --fonte transferegov --ufs RR,AP   # amostra
"""

from __future__ import annotations

import argparse
from datetime import date

FONTES = ("transferegov", "portal", "ibge", "pncp", "querido_diario", "tce", "tce_rs", "congresso")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Carga inicial do Rastro da Emenda")
    parser.add_argument("--fonte", choices=FONTES, required=True)
    parser.add_argument("--desde", default="2024-01-01", help="AAAA-MM-DD")
    parser.add_argument("--ufs", default="", help="lista de UFs separadas por vírgula (amostra)")
    parser.add_argument("--tipo", choices=("contratos", "contratacoes"), default="contratos", help="só para pncp")
    parser.add_argument("--sem-retomar", action="store_true", help="ignora progresso de execução anterior")
    args = parser.parse_args(argv)
    desde = date.fromisoformat(args.desde)
    ufs = [u.strip().upper() for u in args.ufs.split(",") if u.strip()] or None
    retomar = not args.sem_retomar

    if args.fonte == "transferegov":
        from rastro.jobs.carga_transferegov import carregar

        carregar(desde, ufs, retomar=retomar)
    elif args.fonte == "ibge":
        from rastro.jobs.carga_ibge_portal import carregar_ibge

        carregar_ibge()
    elif args.fonte == "portal":
        from rastro.jobs.carga_ibge_portal import carregar_portal

        carregar_portal(desde)
    elif args.fonte == "pncp":
        from rastro.jobs import carga_pncp

        if args.tipo == "contratacoes":
            carga_pncp.carregar_contratacoes(desde, ufs=ufs)
        else:
            carga_pncp.carregar_contratos(desde, ufs=ufs)
    elif args.fonte == "querido_diario":
        from rastro.jobs import carga_querido_diario as cqd

        cqd.atualizar_cobertura()
        cqd.buscar_evidencias(desde, ufs=ufs)
    elif args.fonte == "congresso":
        from rastro.jobs.carga_congresso import carregar_congresso

        carregar_congresso()
    elif args.fonte in ("tce", "tce_rs"):
        from rastro.jobs.carga_tce import CARGAS

        for uf in ufs or (["RS"] if args.fonte == "tce_rs" else list(CARGAS)):
            CARGAS[uf](desde)
    else:
        raise SystemExit(f"fonte {args.fonte} ainda não implementada")


if __name__ == "__main__":
    main()
