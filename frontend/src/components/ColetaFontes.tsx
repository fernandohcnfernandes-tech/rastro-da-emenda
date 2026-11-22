import { CalendarRange, Clock, Database, ExternalLink } from "lucide-react";

import { brlCompacto, data, numero } from "@/lib/formato";

export interface FonteColeta {
  fonte: string;
  nome: string;
  url: string;
  periodo: [string | number | null, string | number | null];
  ultima_coleta: string | null;
  numeros: Record<string, unknown>;
}

const n = (v: unknown) => numero(typeof v === "number" ? v : v == null ? null : Number(v));
const periodo = (p: FonteColeta["periodo"]) => {
  const f = (v: string | number | null) => (v == null ? "…" : typeof v === "number" || /^\d{4}$/.test(String(v)) ? String(v) : data(String(v)));
  return `${f(p[0])} a ${f(p[1] ?? null) === "…" ? "hoje" : f(p[1])}`;
};
const quando = (v: string | null) =>
  v ? new Date(v).toLocaleString("pt-BR", { timeZone: "America/Sao_Paulo", dateStyle: "short", timeStyle: "short" }) : "em andamento";

/** Quantidades coletadas e período abrangido, por fonte. */
function itens(f: FonteColeta): [string, string][] {
  const x = f.numeros;
  switch (f.fonte) {
    case "transferegov":
      return [
        ["Planos de ação (2024+)", n(x.planos)],
        ["Pagamentos (ordens bancárias)", n(x.pagamentos)],
        ["Valor pago", brlCompacto(Number(x.valor_pago ?? 0))],
        ["Empenhos", n(x.empenhos)],
        ["Executores", n(x.executores)],
        ["Metas", n(x.metas)],
        ["Relatórios de gestão", n(x.relatorios)],
      ];
    case "portal":
      return [
        ["Emendas Pix", n(x.emendas)],
        ["Valor pago (CGU)", brlCompacto(Number(x.valor_pago ?? 0))],
        ["Planos com objeto declarado", n(x.objetos)],
        ["Origem dos dados", x.origem === "api" ? "API de dados" : "arquivo oficial de dados abertos"],
      ];
    case "pncp":
      return [
        ["Contratos", n(x.contratos)],
        ["Contratações (licitações, dispensas)", n(x.contratacoes)],
        ["CNPJs consultados", `${n(x.cnpjs_consultados)} de ${n(x.cnpjs_monitorados)}`],
        ["CNPJs com registro no PNCP", n(x.cnpjs_com_registro)],
      ];
    case "tce":
      return [
        ["Contratos", n(x.contratos)],
        ...((x.por_uf as { uf: string; contratos: number; entes: number }[]) ?? []).map(
          (t) => [`TCE-${t.uf}`, `${n(t.contratos)} contratos · ${n(t.entes)} entes`] as [string, string],
        ),
      ];
    case "querido_diario":
      return [
        ["Trechos de diários", n(x.trechos)],
        ["Municípios com trechos", n(x.municipios_com_trechos)],
        ["Territórios com busca de texto", n(x.territorios_cobertos)],
        ["Entes cobertos (inclui DF)", n(x.entes_cobertos)],
      ];
    case "congresso":
      return [
        ["Deputados", n(x.deputados)],
        ["Senadores", n(x.senadores)],
        ["Autores ligados", `${n(x.autores_ligados)} de ${n(x.autores)}`],
      ];
    case "ibge":
      return [
        ["Municípios", n(x.municipios)],
        ["Estimativa populacional", String(x.ano_populacao ?? "—")],
      ];
    default:
      return [];
  }
}

export function ColetaFontes({ fontes }: { fontes: FonteColeta[] }) {
  return (
    <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
      {fontes.map((f) => (
        <article key={f.fonte} className="cartao flex flex-col p-5">
          <div className="flex items-start justify-between gap-3">
            <div className="flex items-center gap-2">
              <span className="grid h-8 w-8 place-items-center rounded-lg bg-primaria/15">
                <Database className="h-4 w-4 text-destaque" />
              </span>
              <h3 className="text-[15px] font-semibold leading-tight text-texto">{f.nome}</h3>
            </div>
            <a href={f.url} target="_blank" rel="noreferrer" className="text-discreto hover:text-destaque" aria-label={`Abrir ${f.nome}`}>
              <ExternalLink className="h-4 w-4" />
            </a>
          </div>
          <dl className="mt-4 flex-1 space-y-1.5 text-sm">
            {itens(f).map(([rotulo, valor]) => (
              <div key={rotulo} className="flex justify-between gap-3 border-b border-borda/40 pb-1.5 last:border-0">
                <dt className="text-apoio">{rotulo}</dt>
                <dd className="text-right font-medium tabular-nums text-texto">{valor}</dd>
              </div>
            ))}
          </dl>
          <div className="mt-4 space-y-1 text-xs text-discreto">
            <p className="flex items-center gap-1.5">
              <CalendarRange className="h-3.5 w-3.5" /> Período abrangido: {periodo(f.periodo)}
            </p>
            <p className="flex items-center gap-1.5">
              <Clock className="h-3.5 w-3.5" /> Última coleta concluída: {quando(f.ultima_coleta)}
            </p>
          </div>
        </article>
      ))}
    </div>
  );
}
