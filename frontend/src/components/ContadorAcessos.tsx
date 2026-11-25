"use client";

import { Eye } from "lucide-react";
import { useEffect, useState } from "react";

import { type Acessos, acessos, esquecerAcessos } from "@/lib/acessos";
import { data, numero } from "@/lib/formato";

/** Selo com o total de acessos ao portal; `comHoje` acrescenta os de hoje (página inicial). */
export function ContadorAcessos({ comHoje = true }: { comHoje?: boolean }) {
  const [dados, setDados] = useState<Acessos | null>(null);

  useEffect(() => {
    let vivo = true;
    acessos().then((d) => {
      if (vivo) setDados(d);
      esquecerAcessos();
    });
    return () => {
      vivo = false;
    };
  }, []);

  if (!dados) return null;
  return (
    <p
      className="inline-flex items-center gap-2 rounded-lg border border-borda/70 bg-superficie/60 px-3 py-1.5 text-sm text-apoio"
      title={dados.desde ? `Contagem desde ${data(dados.desde)} · uma visita por sessão do navegador` : undefined}
    >
      <Eye className="h-4 w-4 text-destaque" aria-hidden />
      <span>
        <strong className="font-semibold tabular-nums text-texto">{numero(dados.total)}</strong> {dados.total === 1 ? "acesso" : "acessos"} ao portal
        {comHoje && <span className="text-discreto"> · {numero(dados.hoje)} hoje</span>}
      </span>
    </p>
  );
}
