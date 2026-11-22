import { Suspense } from "react";

import { ListaEntidades } from "@/components/ListaEntidades";
import { CabecalhoPagina, Cartao, ErroApi, Paginacao } from "@/components/ui";
import { api } from "@/lib/api";
import { UFS, numero } from "@/lib/formato";
import type { MunicipioLista, Pagina } from "@/lib/tipos";

export const metadata = { title: "Municípios" };
type Params = Record<string, string | string[] | undefined>;
const texto = (v: string | string[] | undefined) => (Array.isArray(v) ? v[0] : v) ?? "";

async function Lista({ searchParams }: { searchParams: Promise<Params> }) {
  const sp = await searchParams;
  const busca = texto(sp.q);
  const uf = texto(sp.uf);
  const pagina = Math.max(1, Number(texto(sp.pagina)) || 1);
  const p = new URLSearchParams({ pagina: String(pagina), tamanho: "30" });
  if (busca) p.set("busca", busca);
  if (uf) p.set("uf", uf);
  let lista: Pagina<MunicipioLista>;
  try {
    lista = await api<Pagina<MunicipioLista>>(`/municipios?${p}`);
  } catch {
    return <ErroApi />;
  }
  return (
    <div className="space-y-4">
      <Cartao>
        <form action="/municipios" className="flex flex-wrap gap-2">
          <input name="q" defaultValue={busca} placeholder="Nome do município" className="h-10 min-w-0 flex-1 basis-full rounded-lg sm:basis-auto border border-borda bg-[#070f1d] px-3 text-sm placeholder:text-discreto focus:border-primaria focus:outline-none" />
          <select name="uf" defaultValue={uf} aria-label="UF" className="h-10 rounded-lg border border-borda bg-[#070f1d] px-3 text-sm">
            <option value="">Todas as UFs</option>
            {UFS.map((u) => (
              <option key={u}>{u}</option>
            ))}
          </select>
          <button className="h-10 rounded-lg bg-primaria px-5 text-sm font-medium text-white shadow-primaria hover:bg-primaria-escura">Buscar</button>
        </form>
      </Cartao>
      <p className="text-sm text-apoio">{numero(lista.total)} município(s), do maior para o menor repasse</p>
      <ListaEntidades
        linhas={lista.itens.map((m) => ({
          ...m,
          chave: m.codigo_ibge,
          href: `/municipios/${m.codigo_ibge}`,
          titulo: m.nome,
          subtitulo: `${m.uf} · ${numero(m.populacao)} hab.`,
        }))}
      />
      <Paginacao
        pagina={pagina}
        total={lista.total}
        tamanho={lista.tamanho}
        link={(n) => `/municipios?${new URLSearchParams({ ...(busca && { q: busca }), ...(uf && { uf }), pagina: String(n) })}`}
      />
    </div>
  );
}

export default function PaginaMunicipios({ searchParams }: { searchParams: Promise<Params> }) {
  return (
    <>
      <CabecalhoPagina rotulo="Explorar" titulo="Municípios" descricao="Municípios que receberam emendas Pix desde 2024, com a distribuição do semáforo." />
      <Suspense fallback={<p className="text-sm text-apoio">Carregando…</p>}>
        <Lista searchParams={searchParams} />
      </Suspense>
    </>
  );
}
