import Link from "next/link";
import { Suspense } from "react";

import { Busca } from "@/components/Busca";
import { MapaBrasil } from "@/components/MapaBrasil";
import { ResumoStatus } from "@/components/ResumoStatus";
import { api } from "@/lib/api";
import { numero } from "@/lib/formato";
import type { CoberturaUF, Status } from "@/lib/tipos";

async function Panorama() {
  let cobertura: CoberturaUF[] = [];
  try {
    cobertura = await api<CoberturaUF[]>("/cobertura");
  } catch {
    return <p className="text-sm text-amber-700">API indisponível no momento.</p>;
  }
  const soma = (k: keyof CoberturaUF) => cobertura.reduce((s, c) => s + Number(c[k] ?? 0), 0);
  const contagem: Partial<Record<Status, number>> = {
    verde: soma("verde"),
    amarelo: soma("amarelo"),
    vermelho: soma("vermelho"),
    azul: soma("azul"),
    cinza: soma("cinza"),
  };
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        {[
          ["Emendas Pix (planos de ação)", soma("emendas")],
          ["Entes beneficiários", soma("entes")],
          ["Municípios até 20 mil hab.", soma("municipios_pequenos")],
          ["Pequenos cobertos pelo Querido Diário", soma("pequenos_cobertos_querido_diario")],
        ].map(([rotulo, valor]) => (
          <div key={rotulo} className="rounded-lg border border-slate-200 bg-white p-3">
            <p className="text-2xl font-bold text-[#0B0F1A]">{numero(Number(valor))}</p>
            <p className="text-xs text-slate-500">{rotulo}</p>
          </div>
        ))}
      </div>
      <ResumoStatus contagem={contagem} />
    </div>
  );
}

export default function Inicio() {
  return (
    <div className="space-y-8">
      <section className="rounded-2xl bg-[#0B0F1A] px-6 py-10 text-white sm:px-10">
        <p className="text-sm font-semibold uppercase tracking-widest text-blue-300">Emendas Pix · 2024 até hoje</p>
        <h1 className="mt-2 max-w-3xl text-3xl font-bold leading-tight sm:text-4xl">
          Segue cada real da emenda parlamentar até o contrato no município — e avisa quando o rastro some.
        </h1>
        <p className="mt-3 max-w-2xl text-slate-300">
          Cruzamos Transferegov, Portal da Transparência, PNCP e diários oficiais para mostrar, emenda por emenda, se há evidência de que o
          dinheiro virou licitação e contrato.
        </p>
        <div className="mt-6 max-w-3xl">
          <Busca grande />
        </div>
      </section>

      <section>
        <h2 className="mb-3 text-xl font-bold">Panorama</h2>
        <Suspense fallback={<p className="text-sm text-slate-500">Carregando números…</p>}>
          <Panorama />
        </Suspense>
      </section>

      <MapaBrasil />

      <section className="grid gap-4 sm:grid-cols-3">
        {[
          ["Verde", "Contrato compatível com o objeto e o valor da emenda.", "#16A34A"],
          ["Vermelho", "Pago há mais de 180 dias, sem evidência nas fontes que cobrem o ente. É indício, não acusação.", "#DC2626"],
          ["Azul", "Município pequeno sem fonte pública para verificar. Neutro.", "#2563EB"],
        ].map(([t, d, cor]) => (
          <div key={t} className="rounded-lg border-l-4 bg-white p-4 shadow-sm" style={{ borderColor: cor }}>
            <p className="font-bold">{t}</p>
            <p className="text-sm text-slate-600">{d}</p>
          </div>
        ))}
      </section>
      <p className="text-sm text-slate-500">
        Entenda as regras, as fontes e as limitações em{" "}
        <Link href="/como-funciona" className="text-[#2563EB] hover:underline">
          Como funciona
        </Link>
        .
      </p>
    </div>
  );
}
