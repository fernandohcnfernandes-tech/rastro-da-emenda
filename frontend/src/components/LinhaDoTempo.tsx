import { ExternalLink } from "lucide-react";

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
      <ol className="mb-8 grid grid-cols-5" aria-label="Etapas do caminho do dinheiro">
        {ETAPAS.map((etapa, i) => {
          const ok = presentes.has(etapa.chave);
          return (
            <li key={etapa.chave} className="relative flex flex-col items-center gap-2 text-center text-xs">
              {i > 0 && <span className={`absolute right-1/2 top-4 h-0.5 w-full ${ok ? "bg-primaria" : "bg-borda"}`} aria-hidden />}
              <span
                className={`relative z-10 grid h-8 w-8 place-items-center rounded-full border-2 text-sm font-semibold ${
                  ok ? "border-primaria bg-primaria text-white shadow-primaria" : "border-borda bg-superficie text-discreto"
                }`}
              >
                {i + 1}
              </span>
              <span className={ok ? "font-medium text-texto" : "text-discreto"}>{etapa.nome}</span>
              {!ok && <span className="text-[10px] text-discreto">não localizado</span>}
            </li>
          );
        })}
      </ol>
      <ul className="relative space-y-5 border-l border-borda pl-6">
        {eventos.map((e, i) => (
          <li key={i} className="relative">
            <span className="absolute -left-[31px] top-1.5 h-3 w-3 rounded-full border-2 border-fundo bg-destaque" />
            <p className="text-xs text-discreto">{e.data_aproximada ? `ano de ${e.data.slice(0, 4)}` : data(e.data)}</p>
            <p className="font-medium text-texto">
              {e.titulo}
              {e.valor !== undefined && e.valor !== null && <span className="font-normal text-apoio"> · {brl(e.valor)}</span>}
            </p>
            {e.descricao && <p className="text-sm text-apoio">{e.descricao}</p>}
            {e.url && (
              <a href={e.url} target="_blank" rel="noreferrer" className="mt-1 inline-flex items-center gap-1 text-sm text-destaque hover:underline">
                Documento oficial <ExternalLink className="h-3.5 w-3.5" />
              </a>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}
