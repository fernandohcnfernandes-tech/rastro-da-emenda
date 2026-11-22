import { CORES, ORDEM_STATUS, ROTULOS, numero } from "@/lib/formato";
import type { Status } from "@/lib/tipos";

export function ResumoStatus({ contagem }: { contagem: Partial<Record<Status, number>> }) {
  const total = ORDEM_STATUS.reduce((s, k) => s + (contagem[k] ?? 0), 0);
  if (!total) return <p className="text-sm text-slate-500">Nenhuma emenda avaliada.</p>;
  return (
    <div>
      <div className="flex h-3 w-full overflow-hidden rounded-full bg-slate-100" role="img" aria-label="Distribuição do semáforo">
        {ORDEM_STATUS.map((s) =>
          contagem[s] ? (
            <div key={s} style={{ width: `${(100 * (contagem[s] ?? 0)) / total}%`, backgroundColor: CORES[s] }} title={`${s}: ${contagem[s]}`} />
          ) : null,
        )}
      </div>
      <ul className="mt-3 flex flex-wrap gap-x-5 gap-y-1 text-sm">
        {ORDEM_STATUS.map((s) => (
          <li key={s} className="flex items-center gap-1.5">
            <span className="h-3 w-3 rounded-sm" style={{ backgroundColor: CORES[s] }} />
            <span className="text-[#0B0F1A]">{numero(contagem[s] ?? 0)}</span>
            <span className="text-slate-500">{ROTULOS[s]}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
