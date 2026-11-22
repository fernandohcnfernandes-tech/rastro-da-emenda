"use client";

import { useState } from "react";

/** Abas acessíveis (role=tablist). Os painéis chegam prontos do servidor. */
export function Abas({ abas }: { abas: { id: string; rotulo: string; contador?: number; conteudo: React.ReactNode }[] }) {
  const [atual, setAtual] = useState(abas[0]?.id);
  return (
    <div>
      <div role="tablist" aria-label="Seções da ficha" className="mb-5 flex gap-1 overflow-x-auto border-b border-borda/70">
        {abas.map((a) => (
          <button
            key={a.id}
            role="tab"
            id={`aba-${a.id}`}
            aria-selected={atual === a.id}
            aria-controls={`painel-${a.id}`}
            onClick={() => setAtual(a.id)}
            className={`-mb-px flex min-h-11 items-center gap-2 whitespace-nowrap border-b-2 px-4 text-sm transition ${
              atual === a.id ? "border-primaria text-forte" : "border-transparent text-apoio hover:text-texto"
            }`}
          >
            {a.rotulo}
            {a.contador !== undefined && <span className="rounded-full bg-superficie-3 px-2 text-[11px] tabular-nums text-cinza-claro">{a.contador}</span>}
          </button>
        ))}
      </div>
      {abas.map((a) => (
        <div key={a.id} role="tabpanel" id={`painel-${a.id}`} aria-labelledby={`aba-${a.id}`} hidden={atual !== a.id}>
          {a.conteudo}
        </div>
      ))}
    </div>
  );
}
