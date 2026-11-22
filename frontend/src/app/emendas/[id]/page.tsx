import Link from "next/link";
import { notFound } from "next/navigation";
import { Suspense } from "react";

import { LinhaDoTempo } from "@/components/LinhaDoTempo";
import { StatusBadge } from "@/components/StatusBadge";
import { ErroApi, api } from "@/lib/api";
import { NOME_FONTE, brl, data, numero } from "@/lib/formato";
import type { Ficha } from "@/lib/tipos";

export const metadata = { title: "Ficha da emenda" };

function Campo({ rotulo, children }: { rotulo: string; children: React.ReactNode }) {
  return (
    <div>
      <dt className="text-xs uppercase tracking-wide text-slate-500">{rotulo}</dt>
      <dd className="text-sm text-[#0B0F1A]">{children}</dd>
    </div>
  );
}

async function Conteudo({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  if (!/^\d+$/.test(id)) notFound();
  let f: Ficha;
  try {
    f = await api<Ficha>(`/emendas/${id}`);
  } catch (e) {
    if (e instanceof ErroApi && e.status === 404) notFound();
    return <p className="text-sm text-amber-700">API indisponível no momento.</p>;
  }
  return (
    <div className="space-y-8">
      <header className="space-y-3">
        <p className="text-sm text-slate-500">
          Emenda Pix {f.emenda_numero} · plano de ação {f.codigo_plano_acao}
        </p>
        <h1 className="text-2xl font-bold">{f.beneficiario}</h1>
        <StatusBadge status={f.status} grande />
        <p className="max-w-3xl text-[15px] leading-relaxed">{f.justificativa ?? "Ainda não avaliada."}</p>
        <a
          href={`/api/emendas/${f.id_plano_acao}/dossie.pdf`}
          className="inline-block rounded-md bg-[#2563EB] px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700"
        >
          Baixar dossiê (PDF)
        </a>
      </header>

      {f.alertas_detalhados.length > 0 && (
        <section className="rounded-lg border border-red-200 bg-red-50 p-4">
          <h2 className="font-bold text-[#DC2626]">Alertas — indícios para apuração</h2>
          <ul className="mt-2 space-y-1 text-sm">
            {f.alertas_detalhados.map((a) => (
              <li key={a.codigo}>
                <strong>{a.codigo}</strong> — {a.descricao}
              </li>
            ))}
          </ul>
        </section>
      )}

      <section className="grid gap-6 rounded-xl border border-slate-200 bg-white p-5 md:grid-cols-2">
        <dl className="grid grid-cols-2 gap-4">
          <Campo rotulo="Parlamentar">
            {f.parlamentar ? (
              <Link className="text-[#2563EB] hover:underline" href={`/parlamentares/${encodeURIComponent(f.parlamentar)}`}>
                {f.parlamentar}
              </Link>
            ) : (
              "—"
            )}
          </Campo>
          <Campo rotulo="Município">
            {f.codigo_ibge && f.municipio ? (
              <Link className="text-[#2563EB] hover:underline" href={`/municipios/${f.codigo_ibge}`}>
                {f.municipio} · {f.uf}
              </Link>
            ) : (
              `${f.uf ?? ""} (${f.esfera ?? "—"})`
            )}
          </Campo>
          <Campo rotulo="População (IBGE)">{numero(f.populacao)}</Campo>
          <Campo rotulo="Situação do plano">{f.situacao ?? "—"}</Campo>
          <Campo rotulo="Valor previsto">{brl(f.valor_previsto)}</Campo>
          <Campo rotulo="Repassado">{brl(f.repassado)}</Campo>
          <Campo rotulo="Custeio">{brl(f.valor_custeio)}</Campo>
          <Campo rotulo="Investimento">{brl(f.valor_investimento)}</Campo>
        </dl>
        <div>
          <h2 className="text-xs uppercase tracking-wide text-slate-500">Objeto declarado</h2>
          <p className="mt-1 max-h-64 overflow-y-auto whitespace-pre-line text-sm">{f.objeto_completo ?? "—"}</p>
          {f.executores.some((e) => e.nome_executor !== f.beneficiario) && (
            <p className="mt-3 text-xs text-slate-500">
              Executor(es): {f.executores.map((e) => e.nome_executor).join("; ")}
            </p>
          )}
        </div>
      </section>

      <section className="rounded-xl border border-slate-200 bg-white p-5">
        <h2 className="mb-4 text-lg font-bold">Linha do tempo: indicação → plano de trabalho → pagamento → licitação → contrato</h2>
        <LinhaDoTempo eventos={f.linha_do_tempo} />
      </section>

      <section className="rounded-xl border border-slate-200 bg-white p-5">
        <h2 className="mb-1 text-lg font-bold">Evidências avaliadas</h2>
        <p className="mb-4 text-xs text-slate-500">
          Candidatos do mesmo CNPJ (beneficiário ou executor), a partir do 1º pagamento − 30 dias, com valor entre 10% e 200% do repasse e texto
          parecido. Só contam como evidência os compatíveis com confiança ≥ 60%.
        </p>
        {f.evidencias.length === 0 ? (
          <p className="text-sm text-slate-600">Sem evidência encontrada nas fontes consultadas.</p>
        ) : (
          <ul className="space-y-4">
            {f.evidencias.map((e) => (
              <li key={e.id} className={`rounded-lg border p-4 ${e.conta_como_evidencia ? "border-green-300 bg-green-50/50" : "border-slate-200"}`}>
                <div className="flex flex-wrap items-center gap-2 text-xs">
                  <span className="rounded bg-slate-800 px-2 py-0.5 font-semibold text-white">{NOME_FONTE[e.fonte] ?? e.fonte}</span>
                  <span className={e.conta_como_evidencia ? "font-semibold text-green-700" : "text-slate-500"}>
                    {e.conta_como_evidencia ? "conta como evidência" : "não conta como evidência"} · confiança {Math.round(e.confianca * 100)}%
                    {e.metodo === "heuristica" && " (classificação heurística)"}
                  </span>
                  <span className="text-slate-500">· {data(e.data_assinatura ?? e.data_publicacao)}</span>
                  {e.modalidade && <span className="text-slate-500">· {e.modalidade}</span>}
                </div>
                <p className="mt-2 text-sm">{e.objeto ?? e.trecho}</p>
                <p className="mt-1 text-sm text-slate-600">
                  Valor: {brl(e.valor)}
                  {e.fornecedor_nome && (
                    <>
                      {" "}
                      · Fornecedor: {e.fornecedor_nome} ({e.fornecedor_documento ?? "—"})
                    </>
                  )}
                </p>
                {e.justificativa_ia && <p className="mt-2 text-xs text-slate-500">Análise: {e.justificativa_ia}</p>}
                {e.url && (
                  <a href={e.url} target="_blank" rel="noreferrer" className="mt-2 inline-block text-sm text-[#2563EB] hover:underline">
                    Abrir na fonte oficial ↗
                  </a>
                )}
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="grid gap-6 md:grid-cols-2">
        <div className="rounded-xl border border-slate-200 bg-white p-5">
          <h2 className="mb-2 font-bold">Pagamentos</h2>
          <ul className="space-y-1 text-sm">
            {f.pagamentos.map((p, i) => (
              <li key={i} className="flex justify-between">
                <span>
                  {data(p.data_pagamento)} · {p.numero_ordem_bancaria}
                </span>
                <span className="tabular-nums">{brl(p.valor)}</span>
              </li>
            ))}
            {f.pagamentos.length === 0 && <li className="text-slate-500">Nenhum pagamento registrado.</li>}
          </ul>
        </div>
        <div className="rounded-xl border border-slate-200 bg-white p-5">
          <h2 className="mb-2 font-bold">Relatórios de gestão</h2>
          <ul className="space-y-1 text-sm">
            {f.relatorios_gestao.map((r, i) => (
              <li key={i}>
                {r.tipo ?? "Relatório"} · {r.situacao ?? "—"}
                {r.valor_executado !== null && <> · executado {brl(r.valor_executado)}</>}
              </li>
            ))}
            {f.relatorios_gestao.length === 0 && <li className="text-slate-500">Nenhum relatório de gestão registrado.</li>}
          </ul>
        </div>
      </section>

      <section className="text-sm">
        <h2 className="font-bold">Fontes oficiais</h2>
        <ul className="mt-1 space-y-1">
          {Object.entries(f.fontes)
            .filter(([, url]) => url)
            .map(([nome, url]) => (
              <li key={nome}>
                <a href={url!} target="_blank" rel="noreferrer" className="break-all text-[#2563EB] hover:underline">
                  {nome}: {url}
                </a>
              </li>
            ))}
        </ul>
      </section>
    </div>
  );
}

export default function PaginaEmenda({ params }: { params: Promise<{ id: string }> }) {
  return (
    <Suspense fallback={<p className="text-sm text-slate-500">Carregando ficha da emenda…</p>}>
      <Conteudo params={params} />
    </Suspense>
  );
}
