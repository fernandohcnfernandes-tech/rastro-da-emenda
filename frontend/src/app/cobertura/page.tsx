import { Suspense } from "react";

import { ColetaFontes, type FonteColeta } from "@/components/ColetaFontes";
import { CabecalhoPagina, ErroApi, TituloCartao } from "@/components/ui";
import { api } from "@/lib/api";
import { CORES, ORDEM_STATUS, numero } from "@/lib/formato";
import type { CoberturaUF } from "@/lib/tipos";

export const metadata = { title: "Cobertura das fontes" };

function Pct({ parte, total }: { parte: number; total: number }) {
  const pct = total ? Math.round((100 * parte) / total) : 0;
  return (
    <div className="flex items-center gap-2">
      <div className="h-1.5 w-16 overflow-hidden rounded-full bg-superficie-3">
        <div className="h-full bg-destaque" style={{ width: `${pct}%` }} />
      </div>
      <span className="w-20 tabular-nums text-apoio">
        {numero(parte)} <span className="text-discreto">({pct}%)</span>
      </span>
    </div>
  );
}

async function Tabela() {
  let linhas: CoberturaUF[];
  try {
    linhas = await api<CoberturaUF[]>("/cobertura");
  } catch {
    return <ErroApi />;
  }
  return (
    <div className="cartao overflow-x-auto p-0">
      <table className="w-full min-w-[900px] text-left text-sm">
        <thead className="border-b border-borda/70 text-[11px] uppercase tracking-[0.1em] text-discreto">
          <tr>
            <th className="px-4 py-3">UF</th>
            <th className="px-4 py-3">Entes</th>
            <th className="px-4 py-3">Verificados no PNCP</th>
            <th className="px-4 py-3">Com registro no PNCP</th>
            <th className="px-4 py-3">Tribunal de Contas</th>
            <th className="px-4 py-3">Pequenos no Querido Diário</th>
            <th className="px-4 py-3">Semáforo</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-borda/40">
          {linhas.map((l) => (
            <tr key={l.uf} className="hover:bg-superficie-3/50">
              <td className="px-4 py-3 font-medium">{l.uf}</td>
              <td className="px-4 py-3 tabular-nums">{numero(l.entes)}</td>
              <td className="px-4 py-3"><Pct parte={l.entes_verificados_pncp} total={l.entes} /></td>
              <td className="px-4 py-3"><Pct parte={l.entes_com_registro_pncp} total={l.entes} /></td>
              <td className="px-4 py-3"><Pct parte={l.entes_cobertos_tce ?? 0} total={l.entes} /></td>
              <td className="px-4 py-3"><Pct parte={l.pequenos_cobertos_querido_diario} total={l.municipios_pequenos} /></td>
              <td className="px-4 py-3">
                <div className="flex h-2 w-40 overflow-hidden rounded-full bg-superficie-3">
                  {ORDEM_STATUS.map((s) => (l[s] ? <div key={s} style={{ flex: l[s], background: CORES[s] }} title={`${s}: ${l[s]}`} /> : null))}
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

async function Coleta() {
  let fontes: FonteColeta[];
  try {
    fontes = await api<FonteColeta[]>("/coleta");
  } catch {
    return <ErroApi />;
  }
  return <ColetaFontes fontes={fontes} />;
}

export default function PaginaCobertura() {
  return (
    <>
      <CabecalhoPagina
        rotulo="Análise"
        titulo="Cobertura das fontes"
        descricao="Quanto de cada UF conseguimos verificar: PNCP para todos os entes, Tribunais de Contas onde há dados abertos de contratos e Querido Diário para municípios com até 20 mil habitantes."
      />
      <section className="mb-10">
        <TituloCartao>O que já foi coletado, por fonte</TituloCartao>
        <Suspense fallback={<p className="text-sm text-apoio">Carregando…</p>}>
          <Coleta />
        </Suspense>
      </section>
      <section>
        <TituloCartao>Cobertura por UF</TituloCartao>
        <Suspense fallback={<p className="text-sm text-apoio">Carregando…</p>}>
          <Tabela />
        </Suspense>
      </section>
    </>
  );
}
