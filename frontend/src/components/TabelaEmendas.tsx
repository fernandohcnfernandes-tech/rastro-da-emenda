import Link from "next/link";

import { brl, data } from "@/lib/formato";
import type { EmendaResumo } from "@/lib/tipos";

import { StatusBadge } from "./StatusBadge";

export function TabelaEmendas({ itens, mostrarMunicipio = true }: { itens: EmendaResumo[]; mostrarMunicipio?: boolean }) {
  if (!itens.length) return <p className="py-6 text-sm text-slate-500">Nenhuma emenda encontrada.</p>;
  return (
    <div className="overflow-x-auto rounded-lg border border-slate-200">
      <table className="w-full min-w-[720px] text-left text-sm">
        <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
          <tr>
            <th className="px-3 py-2">Status</th>
            <th className="px-3 py-2">Emenda</th>
            <th className="px-3 py-2">Parlamentar</th>
            {mostrarMunicipio && <th className="px-3 py-2">Beneficiário</th>}
            <th className="px-3 py-2 text-right">Repassado</th>
            <th className="px-3 py-2">1º pagamento</th>
            <th className="px-3 py-2">Alertas</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {itens.map((e) => (
            <tr key={e.id_plano_acao} className="hover:bg-blue-50/40">
              <td className="px-3 py-2">
                <StatusBadge status={e.status} />
              </td>
              <td className="px-3 py-2">
                <Link href={`/emendas/${e.id_plano_acao}`} className="font-medium text-[#2563EB] hover:underline">
                  {e.emenda_numero ?? e.codigo_plano_acao}
                </Link>
                <p className="line-clamp-1 max-w-xs text-xs text-slate-500">{e.objeto}</p>
              </td>
              <td className="px-3 py-2">
                {e.parlamentar ? (
                  <Link href={`/parlamentares/${encodeURIComponent(e.parlamentar)}`} className="hover:underline">
                    {e.parlamentar}
                  </Link>
                ) : (
                  "—"
                )}
              </td>
              {mostrarMunicipio && (
                <td className="px-3 py-2">
                  {e.codigo_ibge && e.municipio ? (
                    <Link href={`/municipios/${e.codigo_ibge}`} className="hover:underline">
                      {e.municipio}
                    </Link>
                  ) : (
                    <span>{e.beneficiario}</span>
                  )}
                  <span className="text-slate-500"> · {e.uf}</span>
                </td>
              )}
              <td className="px-3 py-2 text-right tabular-nums">{brl(e.repassado)}</td>
              <td className="px-3 py-2 tabular-nums">{data(e.primeiro_pagamento)}</td>
              <td className="px-3 py-2 text-xs font-semibold text-[#DC2626]">{e.alertas.join(" ")}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
