import Link from "next/link";

import { brl, data } from "@/lib/formato";
import type { EmendaResumo } from "@/lib/tipos";

import { Selo, Vazio } from "./ui";

export function TabelaEmendas({
  itens,
  mostrarMunicipio = true,
  mostrarParlamentar = true,
}: {
  itens: EmendaResumo[];
  mostrarMunicipio?: boolean;
  mostrarParlamentar?: boolean;
}) {
  if (!itens.length) return <Vazio>Nenhuma emenda encontrada com esses filtros.</Vazio>;
  return (
    <div className="cartao overflow-hidden p-0">
      <div className="overflow-x-auto">
        <table className="w-full min-w-[760px] text-left text-sm">
          <thead className="border-b border-borda/70 text-[11px] uppercase tracking-[0.1em] text-discreto">
            <tr>
              <th className="px-4 py-3 font-semibold">Status</th>
              <th className="px-4 py-3 font-semibold">Emenda</th>
              {mostrarParlamentar && <th className="px-4 py-3 font-semibold">Parlamentar</th>}
              {mostrarMunicipio && <th className="px-4 py-3 font-semibold">Beneficiário</th>}
              <th className="px-4 py-3 text-right font-semibold">Repassado</th>
              <th className="px-4 py-3 font-semibold">1º pagamento</th>
              <th className="px-4 py-3 font-semibold">Alertas</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-borda/40">
            {itens.map((e) => (
              <tr key={e.id_plano_acao} className="transition hover:bg-superficie-3/60">
                <td className="px-4 py-3">
                  <Selo status={e.status} />
                </td>
                <td className="max-w-xs px-4 py-3">
                  <Link href={`/emendas/${e.id_plano_acao}`} className="font-medium text-destaque hover:text-forte hover:underline">
                    {e.emenda_numero ?? e.codigo_plano_acao}
                  </Link>
                  <p className="line-clamp-1 text-xs text-discreto">{e.objeto}</p>
                </td>
                {mostrarParlamentar && (
                <td className="px-4 py-3 text-cinza-claro">
                  {e.parlamentar ? (
                    <Link href={`/parlamentares/${encodeURIComponent(e.parlamentar)}`} className="hover:text-forte hover:underline">
                      {e.parlamentar}
                    </Link>
                  ) : (
                    "—"
                  )}
                </td>
                )}
                {mostrarMunicipio && (
                  <td className="px-4 py-3 text-cinza-claro">
                    {e.codigo_ibge && e.municipio ? (
                      <Link href={`/municipios/${e.codigo_ibge}`} className="hover:text-forte hover:underline">
                        {e.municipio}
                      </Link>
                    ) : (
                      <span>{e.beneficiario}</span>
                    )}
                    <span className="text-discreto"> · {e.uf}</span>
                  </td>
                )}
                <td className="px-4 py-3 text-right tabular-nums text-texto">{brl(e.repassado)}</td>
                <td className="px-4 py-3 tabular-nums text-apoio">{data(e.primeiro_pagamento)}</td>
                <td className="px-4 py-3">
                  <div className="flex flex-wrap gap-1">
                    {e.alertas.map((a) => (
                      <span key={a} className="rounded bg-vermelho/15 px-1.5 py-0.5 text-[11px] font-semibold text-vermelho-claro">
                        {a}
                      </span>
                    ))}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
