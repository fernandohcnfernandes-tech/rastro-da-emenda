import { CORES, ROTULOS } from "@/lib/formato";
import type { Status } from "@/lib/tipos";

export function StatusBadge({ status, grande = false }: { status: Status; grande?: boolean }) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full font-semibold text-white ${grande ? "px-4 py-1.5 text-sm" : "px-2.5 py-0.5 text-xs"}`}
      style={{ backgroundColor: CORES[status] }}
      title={ROTULOS[status]}
    >
      <span className="h-2 w-2 rounded-full bg-white/80" aria-hidden />
      {grande ? `${status.toUpperCase()} · ${ROTULOS[status]}` : status}
    </span>
  );
}
