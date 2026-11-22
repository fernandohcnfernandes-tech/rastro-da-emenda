import { ExternalLink, Mail, Phone } from "lucide-react";
import Link from "next/link";
import { notFound } from "next/navigation";
import { Suspense } from "react";

import { FormAssinatura } from "@/components/FormAssinatura";
import { FotoParlamentar } from "@/components/FotoParlamentar";
import { TabelaEmendas } from "@/components/TabelaEmendas";
import { BarraSemaforo, Cartao, ErroApi, Indicador, Rotulo } from "@/components/ui";
import { ErroApi as ErroDaApi, api } from "@/lib/api";
import { brlCompacto, numero } from "@/lib/formato";
import type { Parlamentar } from "@/lib/tipos";

export const metadata = { title: "Parlamentar" };
const CASA = { camara: "Câmara dos Deputados", senado: "Senado Federal" } as const;

async function Conteudo({ params }: { params: Promise<{ nome: string }> }) {
  const nome = decodeURIComponent((await params).nome);
  let p: Parlamentar;
  try {
    p = await api<Parlamentar>(`/parlamentares/${encodeURIComponent(nome)}`);
  } catch (e) {
    if (e instanceof ErroDaApi && (e.status === 404 || e.status === 422)) notFound();
    return <ErroApi />;
  }
  const perfil = p.perfil;
  return (
    <div className="space-y-6">
      <section className="cartao flex flex-wrap items-center gap-6 p-6">
        <FotoParlamentar url={perfil?.url_foto ?? null} nome={p.nome} tamanho={112} />
        <div className="min-w-0 flex-1 space-y-2">
          <Rotulo>{perfil ? `${CASA[perfil.casa]}${perfil.situacao ? ` · ${perfil.situacao}` : ""}` : "Parlamentar"}</Rotulo>
          <h2 className="text-[28px] font-semibold leading-tight tracking-tight">{perfil?.nome ?? p.nome}</h2>
          {perfil && (
            <p className="text-apoio">
              {perfil.partido ?? "sem partido informado"}
              {perfil.uf && ` · ${perfil.uf}`}
              {perfil.nome_civil && <span className="text-discreto"> · {perfil.nome_civil}</span>}
            </p>
          )}
          {perfil && (
            <div className="flex flex-wrap gap-x-5 gap-y-2 pt-1 text-sm">
              {perfil.email && (
                <a href={`mailto:${perfil.email}`} className="inline-flex items-center gap-1.5 text-destaque hover:underline">
                  <Mail className="h-4 w-4" /> {perfil.email}
                </a>
              )}
              {perfil.telefone && (
                <span className="inline-flex items-center gap-1.5 text-apoio">
                  <Phone className="h-4 w-4" /> {perfil.telefone}
                </span>
              )}
              {perfil.url_pagina && (
                <a href={perfil.url_pagina} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1.5 text-destaque hover:underline">
                  Página oficial <ExternalLink className="h-3.5 w-3.5" />
                </a>
              )}
            </div>
          )}
          {!perfil && <p className="text-sm text-discreto">Não encontramos este autor nos dados abertos da Câmara e do Senado.</p>}
          {p.outros_nomes_encontrados.length > 0 && (
            <p className="text-xs text-discreto">
              Nomes parecidos:{" "}
              {p.outros_nomes_encontrados.map((n, i) => (
                <span key={n}>
                  {i > 0 && ", "}
                  <Link className="text-destaque hover:underline" href={`/parlamentares/${encodeURIComponent(n)}`}>
                    {n}
                  </Link>
                </span>
              ))}
            </p>
          )}
        </div>
      </section>
      <div className="grid gap-4 sm:grid-cols-3">
        <Indicador rotulo="Planos de ação desde 2024" valor={numero(p.total_emendas)} detalhe={`Beneficiários em: ${p.ufs.join(", ") || "—"}`} />
        <Indicador rotulo="Valor repassado" valor={brlCompacto(p.valor_repassado)} />
        <Indicador rotulo="Indícios para apuração" valor={numero(p.status.vermelho ?? 0)} tom="#DC2626" />
      </div>
      <Cartao>
        <BarraSemaforo contagem={p.status} />
      </Cartao>
      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_300px]">
        <TabelaEmendas itens={p.emendas} mostrarParlamentar={false} />
        <FormAssinatura tipo="parlamentar" chave={p.nome} rotulo={p.nome} />
      </div>
      <p className="text-xs text-discreto">Dados do parlamentar: dados abertos da Câmara dos Deputados e do Senado Federal (legislatura 57).</p>
    </div>
  );
}

export default function PaginaParlamentar({ params }: { params: Promise<{ nome: string }> }) {
  return (
    <Suspense fallback={<p className="text-sm text-apoio">Carregando parlamentar…</p>}>
      <Conteudo params={params} />
    </Suspense>
  );
}
