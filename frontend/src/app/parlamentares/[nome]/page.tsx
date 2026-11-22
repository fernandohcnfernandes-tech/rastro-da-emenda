import Link from "next/link";
import { notFound } from "next/navigation";
import { Suspense } from "react";

import { FormAssinatura } from "@/components/FormAssinatura";
import { TabelaEmendas } from "@/components/TabelaEmendas";
import { BarraSemaforo, CabecalhoPagina, Cartao, ErroApi, Indicador } from "@/components/ui";
import { ErroApi as ErroDaApi, api } from "@/lib/api";
import { brlCompacto, numero } from "@/lib/formato";
import type { Parlamentar } from "@/lib/tipos";

export const metadata = { title: "Parlamentar" };

async function Conteudo({ params }: { params: Promise<{ nome: string }> }) {
  const nome = decodeURIComponent((await params).nome);
  let p: Parlamentar;
  try {
    p = await api<Parlamentar>(`/parlamentares/${encodeURIComponent(nome)}`);
  } catch (e) {
    if (e instanceof ErroDaApi && (e.status === 404 || e.status === 422)) notFound();
    return <ErroApi />;
  }
  return (
    <>
      <CabecalhoPagina
        rotulo="Parlamentar"
        titulo={p.nome}
        descricao={
          p.outros_nomes_encontrados.length > 0 && (
            <span className="text-sm">
              Nomes parecidos:{" "}
              {p.outros_nomes_encontrados.map((n, i) => (
                <span key={n}>
                  {i > 0 && ", "}
                  <Link className="text-destaque hover:underline" href={`/parlamentares/${encodeURIComponent(n)}`}>
                    {n}
                  </Link>
                </span>
              ))}
            </span>
          )
        }
      />
      <div className="space-y-6">
        <div className="grid gap-4 sm:grid-cols-3">
          <Indicador rotulo="Planos de ação desde 2024" valor={numero(p.total_emendas)} detalhe={`UF: ${p.ufs.join(", ") || "—"}`} />
          <Indicador rotulo="Valor repassado" valor={brlCompacto(p.valor_repassado)} />
          <Indicador rotulo="Indícios para apuração" valor={numero(p.status.vermelho ?? 0)} tom="#DC2626" />
        </div>
        <Cartao>
          <BarraSemaforo contagem={p.status} />
        </Cartao>
        <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_300px]">
          <TabelaEmendas itens={p.emendas} />
          <FormAssinatura tipo="parlamentar" chave={p.nome} rotulo={p.nome} />
        </div>
      </div>
    </>
  );
}

export default function PaginaParlamentar({ params }: { params: Promise<{ nome: string }> }) {
  return (
    <Suspense fallback={<p className="text-sm text-apoio">Carregando parlamentar…</p>}>
      <Conteudo params={params} />
    </Suspense>
  );
}
