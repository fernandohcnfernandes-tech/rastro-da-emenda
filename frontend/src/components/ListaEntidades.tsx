import Link from "next/link";

import { CORES, ORDEM_STATUS, brlCompacto, numero } from "@/lib/formato";
import type { Contagem, Status } from "@/lib/tipos";

import { Selo, Vazio } from "./ui";

export interface LinhaEntidade extends Contagem {
  chave: string;
  href: string;
  titulo: string;
  subtitulo: string;
  emendas: number;
  repassado: number;
  status: Status;
}

/** Lista em linhas clicáveis com mini-barra do semáforo (municípios e parlamentares). */
export function ListaEntidades({ linhas }: { linhas: LinhaEntidade[] }) {
  if (!linhas.length) return <Vazio>Nada encontrado.</Vazio>;
  return (
    <ul className="space-y-2">
      {linhas.map((l) => (
        <li key={l.chave}>
          <Link
            href={l.href}
            className="flex flex-wrap items-center gap-4 rounded-xl border border-apoio/15 bg-superficie/70 px-4 py-3 transition hover:-translate-y-px hover:border-destaque/50 hover:bg-superficie-2 hover:shadow-cartao"
          >
            <div className="min-w-[180px] flex-1">
              <p className="font-medium text-texto">{l.titulo}</p>
              <p className="text-xs text-discreto">{l.subtitulo}</p>
            </div>
            <div className="flex h-1.5 w-40 overflow-hidden rounded-full bg-superficie-3" aria-hidden>
              {ORDEM_STATUS.map((s) => (l[s] ? <div key={s} style={{ flex: l[s], background: CORES[s] }} /> : null))}
            </div>
            <span className="w-24 text-right text-sm tabular-nums text-apoio">{numero(l.emendas)} emenda(s)</span>
            <span className="w-24 text-right text-sm tabular-nums text-texto">{brlCompacto(l.repassado)}</span>
            <span className="w-24 text-right">
              <Selo status={l.status} />
            </span>
          </Link>
        </li>
      ))}
    </ul>
  );
}
