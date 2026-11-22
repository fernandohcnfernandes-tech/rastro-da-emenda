import { notFound } from "next/navigation";
import { Suspense } from "react";

import { FormAssinatura } from "@/components/FormAssinatura";
import { TabelaEmendas } from "@/components/TabelaEmendas";
import { Aviso, BarraSemaforo, CabecalhoPagina, Cartao, ErroApi, Indicador } from "@/components/ui";
import { ErroApi as ErroDaApi, api } from "@/lib/api";
import { brlCompacto, numero } from "@/lib/formato";
import type { Municipio } from "@/lib/tipos";

export const metadata = { title: "Município" };

async function Conteudo({ params }: { params: Promise<{ codigo: string }> }) {
  const { codigo } = await params;
  if (!/^\d{7}$/.test(codigo)) notFound();
  let m: Municipio;
  try {
    m = await api<Municipio>(`/municipios/${codigo}`);
  } catch (e) {
    if (e instanceof ErroDaApi && e.status === 404) notFound();
    return <ErroApi />;
  }
  return (
    <>
      <CabecalhoPagina
        rotulo={`Município · ${m.uf} · IBGE ${m.codigo_ibge}`}
        titulo={m.nome}
        descricao={`População estimada ${numero(m.populacao)} (${m.ano_populacao ?? "—"})`}
      />
      <div className="space-y-6">
        <div className="grid gap-4 sm:grid-cols-3">
          <Indicador rotulo="Emendas Pix desde 2024" valor={numero(m.emendas.length)} />
          <Indicador rotulo="Valor repassado" valor={brlCompacto(m.valor_repassado)} />
          <Indicador rotulo="Indícios para apuração" valor={numero(m.status.vermelho ?? 0)} tom="#DC2626" />
        </div>
        {m.pequeno && (
          <Aviso tom="azul">
            Município com até 20 mil habitantes: pode publicar contratações só no diário oficial até 2027. Também buscamos no Querido Diário
            {m.coberto_querido_diario ? " (município coberto)" : " — este município não tem cobertura"} e, onde houver, nos dados do Tribunal de Contas.
          </Aviso>
        )}
        <Cartao>
          <BarraSemaforo contagem={m.status} />
        </Cartao>
        <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_300px]">
          <TabelaEmendas itens={m.emendas} mostrarMunicipio={false} />
          <FormAssinatura tipo="municipio" chave={m.codigo_ibge} rotulo={m.nome} />
        </div>
      </div>
    </>
  );
}

export default function PaginaMunicipio({ params }: { params: Promise<{ codigo: string }> }) {
  return (
    <Suspense fallback={<p className="text-sm text-apoio">Carregando município…</p>}>
      <Conteudo params={params} />
    </Suspense>
  );
}
