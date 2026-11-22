import { brl, data } from "@/lib/formato";
import type { Evento } from "@/lib/tipos";

const ETAPAS: { chave: Evento["etapa"]; nome: string }[] = [
  { chave: "indicacao", nome: "Indicação" },
  { chave: "plano_trabalho", nome: "Plano de trabalho" },
  { chave: "pagamento", nome: "Pagamento" },
  { chave: "licitacao", nome: "Licitação" },
  { chave: "contrato", nome: "Contrato" },
];

export function LinhaDoTempo({ eventos }: { eventos: Evento[] }) {
  const presentes = new Set(eventos.map((e) => e.etapa));
  return (
    <div>
      <ol className="mb-6 grid grid-cols-5 gap-1 text-center text-xs" aria-label="Etapas">
        {ETAPAS.map((etapa, i) => {
          const ok = presentes.has(etapa.chave);
          return (
            <li key={etapa.chave} className="flex flex-col items-center gap-1">
              <span
                className={`flex h-8 w-8 items-center justify-center rounded-full border-2 text-sm font-bold ${ok ? "border-[#2563EB] bg-[#2563EB] text-white" : "border-slate-300 bg-white text-slate-400"}`}
              >
                {i + 1}
              </span>
              <span className={ok ? "font-semibold text-[#0B0F1A]" : "text-slate-400"}>{etapa.nome}</span>
              {!ok && <span className="text-[10px] text-slate-400">não localizado</span>}
            </li>
          );
        })}
      </ol>
      <ul className="relative space-y-4 border-l-2 border-slate-200 pl-5">
        {eventos.map((e, i) => (
          <li key={i} className="relative">
            <span className="absolute -left-[27px] top-1 h-3 w-3 rounded-full border-2 border-white bg-[#2563EB]" />
            <p className="text-xs text-slate-500">
              {e.data_aproximada ? `ano de ${e.data.slice(0, 4)}` : data(e.data)}
            </p>
            <p className="font-semibold text-[#0B0F1A]">
              {e.titulo}
              {e.valor !== undefined && e.valor !== null && <span className="font-normal text-slate-600"> · {brl(e.valor)}</span>}
            </p>
            {e.descricao && <p className="text-sm text-slate-600">{e.descricao}</p>}
            {e.url && (
              <a href={e.url} target="_blank" rel="noreferrer" className="text-sm text-[#2563EB] hover:underline">
                Ver documento oficial ↗
              </a>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}
