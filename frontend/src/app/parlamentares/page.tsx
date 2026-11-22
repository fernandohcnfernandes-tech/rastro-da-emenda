import { Suspense } from "react";

import { ListaEntidades } from "@/components/ListaEntidades";
import { CabecalhoPagina, Cartao, ErroApi, Paginacao } from "@/components/ui";
import { api } from "@/lib/api";
import { numero } from "@/lib/formato";
import type { Pagina, ParlamentarLista } from "@/lib/tipos";

export const metadata = { title: "Parlamentares" };
type Params = Record<string, string | string[] | undefined>;
const texto = (v: string | string[] | undefined) => (Array.isArray(v) ? v[0] : v) ?? "";

async function Lista({ searchParams }: { searchParams: Promise<Params> }) {
  const sp = await searchParams;
  const busca = texto(sp.q);
  const pagina = Math.max(1, Number(texto(sp.pagina)) || 1);
  const p = new URLSearchParams({ pagina: String(pagina), tamanho: "30" });
  if (busca) p.set("busca", busca);
  let lista: Pagina<ParlamentarLista>;
  try {
    lista = await api<Pagina<ParlamentarLista>>(`/parlamentares?${p}`);
  } catch {
    return <ErroApi />;
  }
  return (
    <div className="space-y-4">
      <Cartao>
        <form action="/parlamentares" className="flex flex-wrap gap-2">
          <input name="q" defaultValue={busca} placeholder="Nome do parlamentar" className="h-10 min-w-0 flex-1 basis-full rounded-lg sm:basis-auto border border-borda bg-[#070f1d] px-3 text-sm placeholder:text-discreto focus:border-primaria focus:outline-none" />
          <button className="h-10 rounded-lg bg-primaria px-5 text-sm font-medium text-white shadow-primaria hover:bg-primaria-escura">Buscar</button>
        </form>
      </Cartao>
      <p className="text-sm text-apoio">{numero(lista.total)} parlamentar(es), do maior para o menor repasse</p>
      <ListaEntidades
        linhas={lista.itens.map((m) => ({
          ...m,
          chave: m.nome,
          href: `/parlamentares/${encodeURIComponent(m.nome)}`,
          titulo: m.nome,
          subtitulo: `UF dos beneficiários: ${m.ufs.filter(Boolean).join(", ") || "—"}`,
        }))}
      />
      <Paginacao pagina={pagina} total={lista.total} tamanho={lista.tamanho} link={(n) => `/parlamentares?${new URLSearchParams({ ...(busca && { q: busca }), pagina: String(n) })}`} />
    </div>
  );
}

export default function PaginaParlamentares({ searchParams }: { searchParams: Promise<Params> }) {
  return (
    <>
      <CabecalhoPagina rotulo="Explorar" titulo="Parlamentares" descricao="Autores de emendas Pix desde 2024 e o semáforo de execução das emendas que indicaram." />
      <Suspense fallback={<p className="text-sm text-apoio">Carregando…</p>}>
        <Lista searchParams={searchParams} />
      </Suspense>
    </>
  );
}
