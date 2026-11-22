import Link from "next/link";
import { notFound } from "next/navigation";
import { Suspense } from "react";

import { FormAssinatura } from "@/components/FormAssinatura";
import { ResumoStatus } from "@/components/ResumoStatus";
import { TabelaEmendas } from "@/components/TabelaEmendas";
import { ErroApi, api } from "@/lib/api";
import { brl, numero } from "@/lib/formato";
import type { Parlamentar } from "@/lib/tipos";

export const metadata = { title: "Parlamentar" };

async function Conteudo({ params }: { params: Promise<{ nome: string }> }) {
  const nome = decodeURIComponent((await params).nome);
  let p: Parlamentar;
  try {
    p = await api<Parlamentar>(`/parlamentares/${encodeURIComponent(nome)}`);
  } catch (e) {
    if (e instanceof ErroApi && (e.status === 404 || e.status === 422)) notFound();
    return <p className="text-sm text-amber-700">API indisponível no momento.</p>;
  }
  return (
    <div className="space-y-6">
      <header>
        <p className="text-sm text-slate-500">Parlamentar autor de emendas Pix</p>
        <h1 className="text-3xl font-bold">{p.nome}</h1>
        <p className="mt-1 text-sm text-slate-600">
          {numero(p.total_emendas)} plano(s) de ação desde 2024 · {brl(p.valor_repassado)} repassados · UF: {p.ufs.join(", ") || "—"}
        </p>
        {p.outros_nomes_encontrados.length > 0 && (
          <p className="mt-1 text-xs text-slate-500">
            Outros nomes parecidos:{" "}
            {p.outros_nomes_encontrados.map((n, i) => (
              <span key={n}>
                {i > 0 && ", "}
                <Link className="text-[#2563EB] hover:underline" href={`/parlamentares/${encodeURIComponent(n)}`}>
                  {n}
                </Link>
              </span>
            ))}
          </p>
        )}
      </header>
      <ResumoStatus contagem={p.status} />
      <div className="grid gap-6 lg:grid-cols-[1fr_320px]">
        <TabelaEmendas itens={p.emendas} />
        <FormAssinatura tipo="parlamentar" chave={p.nome} rotulo={p.nome} />
      </div>
    </div>
  );
}

export default function PaginaParlamentar({ params }: { params: Promise<{ nome: string }> }) {
  return (
    <Suspense fallback={<p className="text-sm text-slate-500">Carregando parlamentar…</p>}>
      <Conteudo params={params} />
    </Suspense>
  );
}
