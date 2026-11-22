"use client";

import Link from "next/link";
import { useState } from "react";

import { CORES, ORDEM_STATUS, ROTULOS, brlCompacto, numero } from "@/lib/formato";
import type { Resumo } from "@/lib/tipos";

import { Cartao, TituloCartao } from "./ui";

type Medida = "quantidade" | "valor";

/** Barras empilhadas pelo semáforo, por UF, em número de emendas ou em valor repassado. */
export function GraficoUF({ porUf }: { porUf: Resumo["por_uf"] }) {
  const [medida, setMedida] = useState<Medida>("quantidade");
  const total = (u: Resumo["por_uf"][number]) => (medida === "valor" ? u.repassado : u.emendas);
  const parte = (u: Resumo["por_uf"][number], s: (typeof ORDEM_STATUS)[number]) =>
    medida === "valor" ? u[`${s}_valor`] ?? 0 : u[s];
  const ordenadas = [...porUf].sort((a, b) => total(b) - total(a));
  const maior = Math.max(1, ...porUf.map(total));
  return (
    <Cartao>
      <TituloCartao
        extra={
          <div role="group" aria-label="Medida" className="flex overflow-hidden rounded-lg border border-borda text-xs">
            {(
              [
                ["quantidade", "Quantidade"],
                ["valor", "Valor repassado"],
              ] as [Medida, string][]
            ).map(([m, r]) => (
              <button
                key={m}
                type="button"
                aria-pressed={medida === m}
                onClick={() => setMedida(m)}
                className={`h-8 px-3 transition ${medida === m ? "bg-primaria text-white" : "bg-superficie text-apoio hover:text-texto"}`}
              >
                {r}
              </button>
            ))}
          </div>
        }
      >
        Emendas por UF
      </TituloCartao>
      <ul className="grid gap-x-8 gap-y-2 md:grid-cols-2">
        {ordenadas.map((u) => (
          <li key={u.uf} className="flex items-center gap-3 text-sm">
            <Link href={`/emendas?uf=${u.uf}`} className="w-7 font-medium text-cinza-claro hover:text-forte">
              {u.uf}
            </Link>
            <div className="flex h-2 flex-1 overflow-hidden rounded-full bg-superficie-3">
              <div className="flex h-full" style={{ width: `${(100 * total(u)) / maior}%` }}>
                {ORDEM_STATUS.map((s) => {
                  const v = parte(u, s);
                  return v ? <div key={s} title={`${ROTULOS[s]}: ${medida === "valor" ? brlCompacto(v) : numero(v)}`} style={{ flex: v, background: CORES[s] }} /> : null;
                })}
              </div>
            </div>
            <span className="w-20 text-right tabular-nums text-discreto">{medida === "valor" ? brlCompacto(u.repassado) : numero(u.emendas)}</span>
          </li>
        ))}
      </ul>
    </Cartao>
  );
}
