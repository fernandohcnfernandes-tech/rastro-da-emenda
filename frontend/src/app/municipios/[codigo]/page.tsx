import { notFound } from "next/navigation";
import { Suspense } from "react";

import { FormAssinatura } from "@/components/FormAssinatura";
import { ResumoStatus } from "@/components/ResumoStatus";
import { TabelaEmendas } from "@/components/TabelaEmendas";
import { ErroApi, api } from "@/lib/api";
import { brl, numero } from "@/lib/formato";
import type { Municipio } from "@/lib/tipos";

export const metadata = { title: "Município" };

async function Conteudo({ params }: { params: Promise<{ codigo: string }> }) {
  const { codigo } = await params;
  if (!/^\d{7}$/.test(codigo)) notFound();
  let m: Municipio;
  try {
    m = await api<Municipio>(`/municipios/${codigo}`);
  } catch (e) {
    if (e instanceof ErroApi && e.status === 404) notFound();
    return <p className="text-sm text-amber-700">API indisponível no momento.</p>;
  }
  return (
    <div className="space-y-6">
      <header>
        <p className="text-sm text-slate-500">Município · IBGE {m.codigo_ibge}</p>
        <h1 className="text-3xl font-bold">
          {m.nome} <span className="text-slate-400">· {m.uf}</span>
        </h1>
        <p className="mt-1 text-sm text-slate-600">
          População estimada {numero(m.populacao)} ({m.ano_populacao}) · {m.emendas.length} emenda(s) Pix desde 2024 · {brl(m.valor_repassado)} repassados
        </p>
        {m.pequeno && (
          <p className="mt-2 rounded-md bg-blue-50 p-3 text-sm text-blue-900">
            Município com até 20 mil habitantes: pode publicar contratações só no diário oficial até 2027. Buscamos também no Querido Diário
            {m.coberto_querido_diario ? " (município coberto)." : ", mas este município não está na cobertura do projeto."}
          </p>
        )}
      </header>
      <ResumoStatus contagem={m.status} />
      <div className="grid gap-6 lg:grid-cols-[1fr_320px]">
        <TabelaEmendas itens={m.emendas} mostrarMunicipio={false} />
        <FormAssinatura tipo="municipio" chave={m.codigo_ibge} rotulo={m.nome} />
      </div>
    </div>
  );
}

export default function PaginaMunicipio({ params }: { params: Promise<{ codigo: string }> }) {
  return (
    <Suspense fallback={<p className="text-sm text-slate-500">Carregando município…</p>}>
      <Conteudo params={params} />
    </Suspense>
  );
}
