import Link from "next/link";
import { Suspense } from "react";

import { FotoParlamentar } from "@/components/FotoParlamentar";
import { CabecalhoPagina, Cartao, ErroApi, Paginacao, Selo, Vazio } from "@/components/ui";
import { api } from "@/lib/api";
import { CORES, ORDEM_STATUS, UFS, brlCompacto, numero } from "@/lib/formato";
import type { Pagina, ParlamentarLista } from "@/lib/tipos";

export const metadata = { title: "Parlamentares" };
type Params = Record<string, string | string[] | undefined>;
const texto = (v: string | string[] | undefined) => (Array.isArray(v) ? v[0] : v) ?? "";
const NOME_CASA = { camara: "Deputado(a)", senado: "Senador(a)" } as const;

async function Lista({ searchParams }: { searchParams: Promise<Params> }) {
  const sp = await searchParams;
  const f = { q: texto(sp.q), uf: texto(sp.uf), casa: texto(sp.casa), partido: texto(sp.partido) };
  const pagina = Math.max(1, Number(texto(sp.pagina)) || 1);
  const p = new URLSearchParams({ pagina: String(pagina), tamanho: "30" });
  if (f.q) p.set("busca", f.q);
  if (f.uf) p.set("uf", f.uf);
  if (f.casa) p.set("casa", f.casa);
  if (f.partido) p.set("partido", f.partido);
  let lista: Pagina<ParlamentarLista> & { partidos: string[] };
  try {
    lista = await api<Pagina<ParlamentarLista> & { partidos: string[] }>(`/parlamentares?${p}`);
  } catch {
    return <ErroApi />;
  }
  const seletor = "h-10 rounded-lg border border-borda bg-campo px-3 text-sm";
  return (
    <div className="space-y-4">
      <Cartao>
        <form action="/parlamentares" className="flex flex-wrap gap-2">
          <input
            name="q"
            defaultValue={f.q}
            placeholder="Nome do parlamentar"
            className="h-10 min-w-0 flex-1 basis-full rounded-lg border border-borda bg-campo px-3 text-sm placeholder:text-discreto focus:border-primaria focus:outline-none sm:basis-auto"
          />
          <select name="uf" defaultValue={f.uf} aria-label="UF do parlamentar" className={seletor}>
            <option value="">UF do parlamentar</option>
            {UFS.map((u) => (
              <option key={u}>{u}</option>
            ))}
          </select>
          <select name="casa" defaultValue={f.casa} aria-label="Casa" className={seletor}>
            <option value="">Câmara e Senado</option>
            <option value="camara">Câmara</option>
            <option value="senado">Senado</option>
          </select>
          <select name="partido" defaultValue={f.partido} aria-label="Partido" className={seletor}>
            <option value="">Todos os partidos</option>
            {lista.partidos.map((pt) => (
              <option key={pt}>{pt}</option>
            ))}
          </select>
          <button className="h-10 rounded-lg bg-primaria px-5 text-sm font-medium text-white shadow-primaria hover:bg-primaria-escura">Buscar</button>
        </form>
      </Cartao>
      <p className="text-sm text-apoio">{numero(lista.total)} parlamentar(es), do maior para o menor repasse</p>
      {lista.itens.length === 0 ? (
        <Vazio>Nenhum parlamentar encontrado.</Vazio>
      ) : (
        <ul className="space-y-2">
          {lista.itens.map((m) => (
            <li key={m.nome}>
              <Link
                href={`/parlamentares/${encodeURIComponent(m.nome)}`}
                className="flex flex-wrap items-center gap-4 rounded-xl border border-borda/60 bg-superficie px-4 py-3 shadow-cartao transition hover:-translate-y-px hover:border-destaque/60"
              >
                <FotoParlamentar url={m.url_foto} nome={m.nome} />
                <div className="min-w-[180px] flex-1">
                  <p className="font-medium text-texto">{m.nome}</p>
                  <p className="text-xs text-discreto">
                    {m.casa ? NOME_CASA[m.casa] : "Parlamentar"}
                    {m.partido && ` · ${m.partido}`}
                    {m.uf_parlamentar && `-${m.uf_parlamentar}`}
                  </p>
                </div>
                <div className="flex h-1.5 w-40 overflow-hidden rounded-full bg-superficie-3" aria-hidden>
                  {ORDEM_STATUS.map((s) => (m[s] ? <div key={s} style={{ flex: m[s], background: CORES[s] }} /> : null))}
                </div>
                <span className="w-24 text-right text-sm tabular-nums text-apoio">{numero(m.emendas)} emenda(s)</span>
                <span className="w-24 text-right text-sm tabular-nums text-texto">{brlCompacto(m.repassado)}</span>
                <span className="w-24 text-right">
                  <Selo status={m.status} />
                </span>
              </Link>
            </li>
          ))}
        </ul>
      )}
      <Paginacao
        pagina={pagina}
        total={lista.total}
        tamanho={lista.tamanho}
        link={(n) => `/parlamentares?${new URLSearchParams({ ...Object.fromEntries(Object.entries(f).filter(([, v]) => v)), pagina: String(n) })}`}
      />
    </div>
  );
}

export default function PaginaParlamentares({ searchParams }: { searchParams: Promise<Params> }) {
  return (
    <>
      <CabecalhoPagina
        rotulo="Explorar"
        titulo="Parlamentares"
        descricao="Autores de emendas Pix desde 2024. Partido, UF e foto vêm dos dados abertos da Câmara dos Deputados e do Senado Federal."
      />
      <Suspense fallback={<p className="text-sm text-apoio">Carregando…</p>}>
        <Lista searchParams={searchParams} />
      </Suspense>
    </>
  );
}
