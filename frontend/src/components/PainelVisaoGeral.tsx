"use client";

import { AlertTriangle, CheckCircle2, FileText, Landmark } from "lucide-react";
import { useRef, useState } from "react";

import { CORES, brlCompacto, numero } from "@/lib/formato";
import type { Resumo, Status } from "@/lib/tipos";

import { MapaBrasil } from "./MapaBrasil";
import { BarraSemaforo, BotaoLink, Cartao, Indicador, TituloCartao } from "./ui";

const EVIDENCIA: Status[] = ["verde", "amarelo"];

/** Cartões, semáforo e mapa compartilham o mesmo filtro: clicar num cartão ou na legenda filtra o mapa. */
export function PainelVisaoGeral({ resumo: r, lateral }: { resumo: Resumo; lateral: React.ReactNode }) {
  const [filtro, setFiltro] = useState<Status[]>([]);
  const mapa = useRef<HTMLDivElement>(null);
  const igual = (a: Status[]) => a.length === filtro.length && a.every((s) => filtro.includes(s));

  function filtrar(novo: Status[]) {
    setFiltro(igual(novo) ? [] : novo);
    mapa.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  return (
    <>
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Indicador
          rotulo="Emendas Pix (planos de ação)"
          valor={numero(r.emendas)}
          detalhe={`${numero(r.parlamentares)} parlamentares · ${numero(r.entes)} entes`}
          icone={FileText}
          aoClicar={() => filtrar([])}
          ativo={filtro.length === 0}
          dica="Mostrar todas as emendas no mapa"
        />
        <Indicador
          rotulo="Valor repassado"
          valor={brlCompacto(r.valor_repassado)}
          detalhe={`de ${brlCompacto(r.valor_previsto)} previstos`}
          icone={Landmark}
          aoClicar={() => filtrar([])}
          dica="Mostrar todas as emendas no mapa"
        />
        <Indicador
          rotulo="Com evidência de execução"
          valor={r.percentual_com_evidencia === null ? "—" : `${r.percentual_com_evidencia.toLocaleString("pt-BR")}%`}
          detalhe="entre as emendas com fonte verificável · clique para ver no mapa"
          icone={CheckCircle2}
          tom={CORES.verde}
          aoClicar={() => filtrar(EVIDENCIA)}
          ativo={igual(EVIDENCIA)}
          dica="Destacar no mapa os municípios com evidência (verde e amarelo)"
        />
        <Indicador
          rotulo="Indícios para apuração"
          valor={numero(r.status.vermelho ?? 0)}
          detalhe="pagas há mais de 180 dias, sem evidência · clique para ver no mapa"
          icone={AlertTriangle}
          tom={CORES.vermelho}
          aoClicar={() => filtrar(["vermelho"])}
          ativo={igual(["vermelho"])}
          dica="Destacar no mapa os municípios com indício"
        />
      </div>

      <Cartao>
        <TituloCartao extra={filtro.length > 0 && <button onClick={() => setFiltro([])} className="text-xs text-destaque hover:underline">limpar filtro</button>}>
          Semáforo de execução
        </TituloCartao>
        <BarraSemaforo contagem={r.status} selecionados={filtro} aoSelecionar={(s) => filtrar([s])} />
        <p className="mt-2 text-xs text-discreto">Clique numa cor para destacá-la no mapa.</p>
      </Cartao>

      <div ref={mapa} className="grid scroll-mt-24 gap-6 xl:grid-cols-[minmax(0,1fr)_360px]">
        <Cartao>
          <TituloCartao extra={<BotaoLink href="/mapa">Abrir mapa</BotaoLink>}>Mapa por município</TituloCartao>
          <MapaBrasil filtro={filtro} aoFiltrar={setFiltro} />
        </Cartao>
        <div className="space-y-6">{lateral}</div>
      </div>
    </>
  );
}
