import { ArrowRight } from "lucide-react";
import Link from "next/link";
import { Suspense } from "react";

import { Aviso, CabecalhoPagina, ErroApi } from "@/components/ui";
import { api } from "@/lib/api";
import { brlCompacto, numero } from "@/lib/formato";
import type { AlertaResumo } from "@/lib/tipos";

export const metadata = { title: "Alertas" };

async function Lista() {
  let alertas: AlertaResumo[];
  try {
    alertas = await api<AlertaResumo[]>("/alertas");
  } catch {
    return <ErroApi />;
  }
  return (
    <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
      {alertas.map((a) => (
        <Link
          key={a.codigo}
          href={`/emendas?alerta=${a.codigo}`}
          className="cartao group flex flex-col p-5 transition hover:-translate-y-px hover:border-destaque/50"
        >
          <span className="w-fit rounded-md bg-vermelho/15 px-2 py-1 text-xs font-semibold text-vermelho-claro">{a.codigo}</span>
          <p className="mt-3 flex-1 text-sm leading-relaxed text-cinza-claro">{a.descricao}</p>
          <div className="mt-4 flex items-end justify-between">
            <div>
              <p className="text-2xl font-semibold tabular-nums">{numero(a.emendas)}</p>
              <p className="text-xs text-discreto">emendas · {brlCompacto(a.repassado)}</p>
            </div>
            <ArrowRight className="h-5 w-5 text-discreto transition group-hover:translate-x-0.5 group-hover:text-destaque" />
          </div>
        </Link>
      ))}
    </div>
  );
}

export default function PaginaAlertas() {
  return (
    <>
      <CabecalhoPagina rotulo="Análise" titulo="Alertas" descricao="Regras que destacam indícios para apuração. Uma emenda pode ter mais de um alerta; clique para ver as emendas." />
      <div className="mb-6">
        <Aviso tom="amarelo">Alertas são indícios calculados a partir de dados públicos, não conclusões. Confira sempre os documentos oficiais na ficha da emenda.</Aviso>
      </div>
      <Suspense fallback={<p className="text-sm text-apoio">Carregando…</p>}>
        <Lista />
      </Suspense>
    </>
  );
}
