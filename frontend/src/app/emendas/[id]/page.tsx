import { Download, ExternalLink } from "lucide-react";
import Link from "next/link";
import { notFound } from "next/navigation";
import { Suspense } from "react";

import { Abas } from "@/components/Abas";
import { LinhaDoTempo } from "@/components/LinhaDoTempo";
import { Aviso, BotaoLink, Cartao, ErroApi, Rotulo, Selo, TituloCartao, Vazio } from "@/components/ui";
import { ErroApi as ErroDaApi, api } from "@/lib/api";
import { CORES, NOME_FONTE, brl, data, numero } from "@/lib/formato";
import type { Ficha } from "@/lib/tipos";

export const metadata = { title: "Ficha da emenda" };

function Campo({ rotulo, children }: { rotulo: string; children: React.ReactNode }) {
  return (
    <div>
      <dt className="text-xs text-discreto">{rotulo}</dt>
      <dd className="mt-0.5 text-sm text-texto">{children}</dd>
    </div>
  );
}

function BarraConfianca({ valor, conta }: { valor: number; conta: boolean }) {
  return (
    <div className="flex items-center gap-2" title={`Confiança ${Math.round(valor * 100)}%`}>
      <div className="relative h-1.5 w-24 overflow-hidden rounded-full bg-superficie-3">
        <div className="h-full" style={{ width: `${valor * 100}%`, background: conta ? CORES.verde : valor >= 0.45 ? CORES.amarelo : CORES.cinza }} />
        <span className="absolute inset-y-0 left-[60%] w-px bg-white/40" aria-hidden />
      </div>
      <span className="text-xs tabular-nums text-apoio">{Math.round(valor * 100)}%</span>
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
    if (e instanceof ErroDaApi && e.status === 404) notFound();
    return <ErroApi />;
  }
  const validas = f.evidencias.filter((e) => e.conta_como_evidencia).length;

  const resumo = (
    <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_340px]">
      <Cartao>
        <TituloCartao>Objeto declarado</TituloCartao>
        <p className="max-h-80 overflow-y-auto whitespace-pre-line text-sm leading-relaxed text-cinza-claro">{f.objeto_completo ?? "—"}</p>
        {f.executores.some((e) => e.nome_executor !== f.beneficiario) && (
          <p className="mt-4 text-xs text-discreto">Executor(es): {f.executores.map((e) => e.nome_executor).join("; ")}</p>
        )}
      </Cartao>
      <Cartao>
        <dl className="grid grid-cols-2 gap-4">
          <Campo rotulo="Parlamentar">
            {f.parlamentar ? (
              <Link className="text-destaque hover:underline" href={`/parlamentares/${encodeURIComponent(f.parlamentar)}`}>
                {f.parlamentar}
              </Link>
            ) : (
              "—"
            )}
          </Campo>
          <Campo rotulo="Município">
            {f.codigo_ibge && f.municipio ? (
              <Link className="text-destaque hover:underline" href={`/municipios/${f.codigo_ibge}`}>
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
      </Cartao>
    </div>
  );

  const evidencias =
    f.evidencias.length === 0 ? (
      <Vazio>Sem evidência encontrada nas fontes consultadas.</Vazio>
    ) : (
      <div className="space-y-3">
        <p className="text-xs text-discreto">
          Candidatos do mesmo CNPJ (beneficiário ou executor), a partir do 1º pagamento − 30 dias, com valor entre 10% e 200% do repasse e
          texto parecido. Só contam como evidência os compatíveis com confiança ≥ 60% (linha branca na barra).
        </p>
        {f.evidencias.map((e) => (
          <article key={e.id} className={`cartao p-4 ${e.conta_como_evidencia ? "border-verde/50" : ""}`}>
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="flex flex-wrap items-center gap-2 text-xs">
                <span className="rounded-md bg-superficie-3 px-2 py-1 font-medium text-cinza-claro">{NOME_FONTE[e.fonte] ?? e.fonte}</span>
                <span className={e.conta_como_evidencia ? "font-medium text-verde-claro" : "text-apoio"}>
                  {e.conta_como_evidencia ? "conta como evidência" : e.compativel && e.confianca >= 0.45 ? "em revisão" : "não conta como evidência"}
                </span>
                {e.metodo === "heuristica" && <span className="text-discreto">· classificação heurística</span>}
                <span className="text-discreto">· {data(e.data_assinatura ?? e.data_publicacao)}</span>
                {e.modalidade && <span className="text-discreto">· {e.modalidade}</span>}
              </div>
              <BarraConfianca valor={e.confianca} conta={e.conta_como_evidencia} />
            </div>
            <p className="mt-3 text-sm leading-relaxed text-texto">{e.objeto ?? e.trecho}</p>
            <p className="mt-2 text-sm text-apoio">
              {brl(e.valor)}
              {e.fornecedor_nome && (
                <>
                  {" "}
                  · {e.fornecedor_nome} ({e.fornecedor_documento ?? "—"})
                </>
              )}
            </p>
            {e.justificativa_ia && <p className="mt-2 text-xs text-discreto">Análise: {e.justificativa_ia}</p>}
            {e.url && (
              <a href={e.url} target="_blank" rel="noreferrer" className="mt-2 inline-flex items-center gap-1 text-sm text-destaque hover:underline">
                Abrir na fonte oficial <ExternalLink className="h-3.5 w-3.5" />
              </a>
            )}
          </article>
        ))}
      </div>
    );

  const pagamentos = (
    <div className="grid gap-6 lg:grid-cols-2">
      <Cartao>
        <TituloCartao>Pagamentos (ordens bancárias)</TituloCartao>
        <ul className="divide-y divide-borda/50 text-sm">
          {f.pagamentos.map((p, i) => (
            <li key={i} className="flex justify-between py-2">
              <span className="text-apoio">
                {data(p.data_pagamento)} · {p.numero_ordem_bancaria}
              </span>
              <span className="tabular-nums">{brl(p.valor)}</span>
            </li>
          ))}
          {f.pagamentos.length === 0 && <li className="py-2 text-apoio">Nenhum pagamento registrado.</li>}
        </ul>
      </Cartao>
      <Cartao>
        <TituloCartao>Relatórios de gestão</TituloCartao>
        <ul className="divide-y divide-borda/50 text-sm">
          {f.relatorios_gestao.map((r, i) => (
            <li key={i} className="flex justify-between py-2">
              <span className="text-apoio">
                {r.tipo ?? "Relatório"} · {r.situacao ?? "—"}
              </span>
              {r.valor_executado !== null && <span className="tabular-nums">{brl(r.valor_executado)}</span>}
            </li>
          ))}
          {f.relatorios_gestao.length === 0 && <li className="py-2 text-apoio">Nenhum relatório de gestão registrado.</li>}
        </ul>
      </Cartao>
    </div>
  );

  const fontes = (
    <Cartao>
      <TituloCartao>Fontes oficiais</TituloCartao>
      <ul className="space-y-2 text-sm">
        {Object.entries(f.fontes)
          .filter(([, url]) => url)
          .map(([nome, url]) => (
            <li key={nome}>
              <a href={url!} target="_blank" rel="noreferrer" className="break-all text-destaque hover:underline">
                {nome}: {url}
              </a>
            </li>
          ))}
      </ul>
    </Cartao>
  );

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0 space-y-3">
          <Rotulo>
            Emenda Pix {f.emenda_numero} · plano {f.codigo_plano_acao}
          </Rotulo>
          <h2 className="text-[28px] font-semibold leading-tight tracking-tight">{f.beneficiario}</h2>
          <Selo status={f.status} grande />
        </div>
        <BotaoLink href={`/api/emendas/${f.id_plano_acao}/dossie.pdf`} primario externo>
          <Download className="h-4 w-4" /> Baixar dossiê (PDF)
        </BotaoLink>
      </header>
      <p className="max-w-4xl text-[15px] leading-relaxed text-cinza-claro">{f.justificativa ?? "Ainda não avaliada."}</p>
      {f.alertas_detalhados.length > 0 && (
        <Aviso>
          <p className="font-semibold">Alertas — indícios para apuração</p>
          <ul className="mt-1 space-y-0.5">
            {f.alertas_detalhados.map((a) => (
              <li key={a.codigo}>
                <strong>{a.codigo}</strong> — {a.descricao}
              </li>
            ))}
          </ul>
        </Aviso>
      )}
      <Abas
        abas={[
          { id: "resumo", rotulo: "Resumo", conteudo: resumo },
          {
            id: "linha",
            rotulo: "Linha do tempo",
            conteudo: (
              <Cartao>
                <LinhaDoTempo eventos={f.linha_do_tempo} />
              </Cartao>
            ),
          },
          { id: "evidencias", rotulo: validas ? `Evidências (${validas} válida${validas > 1 ? "s" : ""})` : "Evidências", contador: f.evidencias.length, conteudo: evidencias },
          { id: "pagamentos", rotulo: "Pagamentos", contador: f.pagamentos.length, conteudo: pagamentos },
          { id: "fontes", rotulo: "Fontes", conteudo: fontes },
        ]}
      />
    </div>
  );
}

export default function PaginaEmenda({ params }: { params: Promise<{ id: string }> }) {
  return (
    <Suspense fallback={<p className="text-sm text-apoio">Carregando ficha da emenda…</p>}>
      <Conteudo params={params} />
    </Suspense>
  );
}
