import Link from "next/link";
import { Suspense } from "react";

import { Busca } from "@/components/Busca";
import { ResumoStatus } from "@/components/ResumoStatus";
import { TabelaEmendas } from "@/components/TabelaEmendas";
import { api } from "@/lib/api";
import { ORDEM_STATUS, numero } from "@/lib/formato";
import type { ListaEmendas } from "@/lib/tipos";

export const metadata = { title: "Emendas" };

type Params = Record<string, string | string[] | undefined>;

function texto(v: string | string[] | undefined): string {
  return (Array.isArray(v) ? v[0] : v) ?? "";
}

async function Resultados({ searchParams }: { searchParams: Promise<Params> }) {
  const sp = await searchParams;
  const q = texto(sp.q);
  const status = texto(sp.status);
  const uf = texto(sp.uf);
  const pagina = Math.max(1, Number(texto(sp.pagina)) || 1);
  const params = new URLSearchParams({ pagina: String(pagina), tamanho: "25" });
  if (q) params.set("busca", q);
  if (status) params.set("status", status);
  if (uf) params.set("uf", uf);
  let lista: ListaEmendas;
  try {
    lista = await api<ListaEmendas>(`/emendas?${params}`);
  } catch {
    return <p className="text-sm text-amber-700">API indisponível no momento.</p>;
  }
  const paginas = Math.max(1, Math.ceil(lista.total / lista.tamanho));
  const link = (mudancas: Record<string, string>) => {
    const p = new URLSearchParams({ q, status, uf, pagina: String(pagina), ...mudancas });
    for (const [k, v] of [...p.entries()]) if (!v) p.delete(k);
    return `/busca?${p}`;
  };
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2 text-sm">
        <span className="text-slate-500">Status:</span>
        {["", ...ORDEM_STATUS].map((s) => (
          <Link
            key={s || "todos"}
            href={link({ status: s, pagina: "1" })}
            className={`rounded-full border px-3 py-1 ${status === s ? "border-[#2563EB] bg-[#2563EB] text-white" : "border-slate-300 bg-white"}`}
          >
            {s || "todos"}
          </Link>
        ))}
      </div>
      <ResumoStatus contagem={lista.resumo_status} />
      <p className="text-sm text-slate-600">
        {numero(lista.total)} emenda(s) encontrada(s){q && <> para “{q}”</>}. Página {pagina} de {paginas}.
      </p>
      <TabelaEmendas itens={lista.itens} />
      <div className="flex justify-between text-sm">
        {pagina > 1 ? <Link href={link({ pagina: String(pagina - 1) })} className="text-[#2563EB]">← Anterior</Link> : <span />}
        {pagina < paginas && <Link href={link({ pagina: String(pagina + 1) })} className="text-[#2563EB]">Próxima →</Link>}
      </div>
    </div>
  );
}

async function CampoBusca({ searchParams }: { searchParams: Promise<Params> }) {
  return <Busca valor={texto((await searchParams).q)} />;
}

export default function PaginaBusca({ searchParams }: { searchParams: Promise<Params> }) {
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Emendas Pix</h1>
      <Suspense fallback={<Busca />}>
        <CampoBusca searchParams={searchParams} />
      </Suspense>
      <Suspense fallback={<p className="text-sm text-slate-500">Buscando…</p>}>
        <Resultados searchParams={searchParams} />
      </Suspense>
    </div>
  );
}
