import { Suspense } from "react";

import { TabelaEmendas } from "@/components/TabelaEmendas";
import { BarraSemaforo, CabecalhoPagina, Cartao, Chip, ErroApi, Paginacao } from "@/components/ui";
import { api } from "@/lib/api";
import { ORDEM_STATUS, UFS, numero } from "@/lib/formato";
import type { ListaEmendas } from "@/lib/tipos";

export const metadata = { title: "Emendas" };

type Params = Record<string, string | string[] | undefined>;
const texto = (v: string | string[] | undefined) => (Array.isArray(v) ? v[0] : v) ?? "";
const ALERTAS = ["A1", "A2", "A3", "A4", "A5", "A6", "A7"];
const ORDENS: [string, string][] = [
  ["repassado", "Maior repasse"],
  ["recentes", "Pagas recentemente"],
  ["antigas", "Pagas há mais tempo"],
];

async function Resultados({ searchParams }: { searchParams: Promise<Params> }) {
  const sp = await searchParams;
  const f = {
    q: texto(sp.q),
    status: texto(sp.status),
    uf: texto(sp.uf),
    alerta: texto(sp.alerta),
    esfera: texto(sp.esfera),
    ordem: texto(sp.ordem) || "repassado",
  };
  const pagina = Math.max(1, Number(texto(sp.pagina)) || 1);
  const params = new URLSearchParams({ pagina: String(pagina), tamanho: "25", ordem: f.ordem });
  if (f.q) params.set("busca", f.q);
  if (f.status) params.set("status", f.status);
  if (f.uf) params.set("uf", f.uf);
  if (f.alerta) params.set("alerta", f.alerta);
  if (f.esfera) params.set("esfera", f.esfera);
  let lista: ListaEmendas;
  try {
    lista = await api<ListaEmendas>(`/emendas?${params}`);
  } catch {
    return <ErroApi />;
  }
  const link = (mudancas: Record<string, string>) => {
    const p = new URLSearchParams({ ...f, pagina: String(pagina), ...mudancas });
    for (const [k, v] of [...p.entries()]) if (!v || (k === "ordem" && v === "repassado") || (k === "pagina" && v === "1")) p.delete(k);
    const s = p.toString();
    return s ? `/emendas?${s}` : "/emendas";
  };
  return (
    <div className="space-y-5">
      <Cartao className="space-y-4">
        <form action="/emendas" className="flex flex-wrap gap-2">
          <input
            name="q"
            defaultValue={f.q}
            placeholder="Município, parlamentar, número da emenda ou objeto (ex.: ambulância)"
            className="h-10 min-w-0 flex-1 basis-full rounded-lg sm:basis-auto border border-borda bg-campo px-3 text-sm placeholder:text-discreto focus:border-primaria focus:outline-none"
          />
          <select name="uf" defaultValue={f.uf} aria-label="UF" className="h-10 rounded-lg border border-borda bg-campo px-3 text-sm">
            <option value="">Todas as UFs</option>
            {UFS.map((u) => (
              <option key={u}>{u}</option>
            ))}
          </select>
          {f.status && <input type="hidden" name="status" value={f.status} />}
          {f.alerta && <input type="hidden" name="alerta" value={f.alerta} />}
          {f.esfera && <input type="hidden" name="esfera" value={f.esfera} />}
          <button className="h-10 rounded-lg bg-primaria px-5 text-sm font-medium text-white shadow-primaria hover:bg-primaria-escura">Filtrar</button>
        </form>
        <div className="flex flex-wrap items-center gap-2">
          <span className="w-16 text-xs text-discreto">Esfera</span>
          {(
            [
              ["", "todas"],
              ["municipal", "municípios"],
              ["estadual", "estados e DF"],
            ] as [string, string][]
          ).map(([v, r]) => (
            <Chip key={v || "todas"} href={link({ esfera: v, pagina: "1" })} ativo={f.esfera === v}>
              {r}
            </Chip>
          ))}
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <span className="w-16 text-xs text-discreto">Status</span>
          <Chip href={link({ status: "", pagina: "1" })} ativo={!f.status}>
            todos
          </Chip>
          {ORDEM_STATUS.map((s) => (
            <Chip key={s} href={link({ status: s, pagina: "1" })} ativo={f.status === s}>
              {s}
            </Chip>
          ))}
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <span className="w-16 text-xs text-discreto">Alerta</span>
          <Chip href={link({ alerta: "", pagina: "1" })} ativo={!f.alerta}>
            todos
          </Chip>
          {ALERTAS.map((a) => (
            <Chip key={a} href={link({ alerta: a, pagina: "1" })} ativo={f.alerta === a}>
              {a}
            </Chip>
          ))}
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <span className="w-16 text-xs text-discreto">Ordem</span>
          {ORDENS.map(([o, r]) => (
            <Chip key={o} href={link({ ordem: o, pagina: "1" })} ativo={f.ordem === o}>
              {r}
            </Chip>
          ))}
        </div>
      </Cartao>
      <BarraSemaforo contagem={lista.resumo_status} />
      <p className="text-sm text-apoio">
        {numero(lista.total)} emenda(s){f.q && <> para “{f.q}”</>}
      </p>
      <TabelaEmendas itens={lista.itens} />
      <Paginacao pagina={pagina} total={lista.total} tamanho={lista.tamanho} link={(p) => link({ pagina: String(p) })} />
    </div>
  );
}

export default function PaginaEmendas({ searchParams }: { searchParams: Promise<Params> }) {
  return (
    <>
      <CabecalhoPagina rotulo="Explorar" titulo="Emendas Pix" descricao="Todos os planos de ação de transferências especiais desde 2024, com o semáforo de execução e os alertas." />
      <Suspense fallback={<p className="text-sm text-apoio">Buscando…</p>}>
        <Resultados searchParams={searchParams} />
      </Suspense>
    </>
  );
}
