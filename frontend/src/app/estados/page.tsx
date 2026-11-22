import { Suspense } from "react";

import { ListaEntidades } from "@/components/ListaEntidades";
import { MapaBrasil } from "@/components/MapaBrasil";
import { CabecalhoPagina, Cartao, ErroApi } from "@/components/ui";
import { api } from "@/lib/api";
import { numero } from "@/lib/formato";
import type { Contagem, Status } from "@/lib/tipos";

export const metadata = { title: "Estados e DF" };

interface Estado extends Contagem {
  uf: string;
  nome: string;
  populacao: number | null;
  coberto_tce: string | null;
  coberto_querido_diario: boolean;
  emendas: number;
  repassado: number;
  status: Status;
}

async function Lista() {
  let estados: Estado[];
  try {
    estados = await api<Estado[]>("/mapa/estados");
  } catch {
    return <ErroApi />;
  }
  const ordenados = [...estados].sort((a, b) => b.repassado - a.repassado);
  return (
    <ListaEntidades
      linhas={ordenados.map((e) => ({
        ...e,
        chave: e.uf,
        href: `/emendas?uf=${e.uf}&esfera=estadual`,
        titulo: e.nome,
        subtitulo: [
          `${e.uf} · ${numero(e.populacao)} hab.`,
          "fontes: PNCP",
          e.coberto_tce && e.coberto_tce,
          e.coberto_querido_diario && "Querido Diário (DODF)",
        ]
          .filter(Boolean)
          .join(" · "),
      }))}
    />
  );
}

export default function PaginaEstados() {
  return (
    <>
      <CabecalhoPagina
        rotulo="Explorar"
        titulo="Estados e Distrito Federal"
        descricao="Emendas Pix destinadas aos governos estaduais e ao DF. A verificação usa os CNPJs do estado e dos órgãos executores (secretarias) no PNCP e, onde há dados abertos, os contratos estaduais informados ao Tribunal de Contas; no DF, também o Diário Oficial pelo Querido Diário."
      />
      <div className="space-y-6">
        <Cartao>
          <MapaBrasil camadaInicial="estados" painel />
        </Cartao>
        <Suspense fallback={<p className="text-sm text-apoio">Carregando…</p>}>
          <Lista />
        </Suspense>
      </div>
    </>
  );
}
