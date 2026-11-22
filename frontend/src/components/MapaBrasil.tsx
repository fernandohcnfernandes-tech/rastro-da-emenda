"use client";

import { geoMercator, geoPath } from "d3-geo";
import { select } from "d3-selection";
import "d3-transition";
import { type ZoomBehavior, type ZoomTransform, zoom, zoomIdentity } from "d3-zoom";
import type { Feature, FeatureCollection, Geometry } from "geojson";
import { ArrowRight, Maximize2, Minus, Plus, X } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useRef, useState } from "react";

import { CORES, CORES_TEXTO, ORDEM_STATUS, ROTULOS, UFS, brlCompacto, numero } from "@/lib/formato";
import type { PontoMapa, Status } from "@/lib/tipos";

type Municipio = Feature<Geometry, { c: string }>;

const LARGURA = 800;
const ALTURA = 780;
const PREFIXO_UF: Record<string, string> = {
  RO: "11", AC: "12", AM: "13", RR: "14", PA: "15", AP: "16", TO: "17", MA: "21", PI: "22", CE: "23", RN: "24",
  PB: "25", PE: "26", AL: "27", SE: "28", BA: "29", MG: "31", ES: "32", RJ: "33", SP: "35", PR: "41", SC: "42",
  RS: "43", MS: "50", MT: "51", GO: "52", DF: "53",
};
const SIGLA_POR_CODIGO = Object.fromEntries(Object.entries(PREFIXO_UF).map(([sigla, codigo]) => [codigo, sigla]));
type Camada = "municipios" | "estados";
const SEM_EMENDA = "var(--t-mapa-vazio)";
const FILTRADO = "var(--t-mapa-filtrado)";
const ZOOM_MAXIMO = 24;
const BOTOES_ZOOM = [
  { rotulo: "Aproximar", icone: Plus, fator: 1.8 },
  { rotulo: "Afastar", icone: Minus, fator: 1 / 1.8 },
  { rotulo: "Ver tudo", icone: Maximize2, fator: null },
];

export function MapaBrasil({
  painel = false,
  altura = "",
  filtro: filtroExterno,
  aoFiltrar,
  camadaInicial = "municipios",
}: {
  painel?: boolean;
  altura?: string;
  /** Filtro controlado de fora (ex.: cartões da visão geral). Vazio = todos os status. */
  filtro?: Status[];
  aoFiltrar?: (filtro: Status[]) => void;
  /** Municípios ou governos estaduais e do DF. */
  camadaInicial?: Camada;
}) {
  const router = useRouter();
  const [malha, setMalha] = useState<FeatureCollection<Geometry, { c: string }> | null>(null);
  const [pontos, setPontos] = useState<Map<string, PontoMapa>>(new Map());
  const [malhaUf, setMalhaUf] = useState<FeatureCollection<Geometry, { c: string }> | null>(null);
  const [pontosUf, setPontosUf] = useState<Map<string, PontoMapa>>(new Map());
  const [camada, setCamada] = useState<Camada>(camadaInicial);
  const [uf, setUf] = useState("");
  const [filtroInterno, setFiltroInterno] = useState<Status[]>([]);
  const filtro = filtroExterno ?? filtroInterno;
  const setFiltro = aoFiltrar ?? setFiltroInterno;
  function alternarStatus(s: Status) {
    setFiltro(filtro.length === 1 && filtro[0] === s ? [] : [s]);
  }
  const [foco, setFoco] = useState<{ ponto?: PontoMapa; codigo: string; x: number; y: number } | null>(null);
  const [selecionado, setSelecionado] = useState<PontoMapa | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [transformacao, setTransformacao] = useState<ZoomTransform>(zoomIdentity);
  const svgRef = useRef<SVGSVGElement>(null);
  const zoomRef = useRef<ZoomBehavior<SVGSVGElement, unknown> | null>(null);

  useEffect(() => {
    fetch("/malha/municipios.json")
      .then((r) => r.json())
      .then(setMalha)
      .catch(() => setErro("Não foi possível carregar a malha do IBGE."));
    fetch("/api/mapa")
      .then((r) => (r.ok ? r.json() : Promise.reject(r.status)))
      .then((lista: PontoMapa[]) => setPontos(new Map(lista.map((p) => [p.codigo_ibge, p]))))
      .catch(() => setErro("API indisponível: o mapa aparece sem cores."));
    fetch("/malha/ufs.json")
      .then((r) => r.json())
      .then(setMalhaUf)
      .catch(() => undefined);
    fetch("/api/mapa/estados")
      .then((r) => (r.ok ? r.json() : Promise.reject(r.status)))
      .then((lista: (Omit<PontoMapa, "codigo_ibge" | "municipio"> & { nome: string })[]) =>
        setPontosUf(
          new Map(
            lista.map((e) => [PREFIXO_UF[e.uf], { ...e, codigo_ibge: PREFIXO_UF[e.uf], municipio: e.nome } as PontoMapa]),
          ),
        ),
      )
      .catch(() => undefined);
  }, []);

  const estados = camada === "estados";
  const ativos = estados ? pontosUf : pontos;
  const destino = (p: PontoMapa) => (estados ? `/emendas?uf=${p.uf}&esfera=estadual` : `/municipios/${p.codigo_ibge}`);

  const feicoes = useMemo<Municipio[]>(() => {
    if (estados) return malhaUf?.features ?? [];
    if (!malha) return [];
    return uf ? malha.features.filter((f) => f.properties.c.startsWith(PREFIXO_UF[uf])) : malha.features;
  }, [malha, malhaUf, uf, estados]);

  const caminho = useMemo(() => {
    if (!feicoes.length) return null;
    const projecao = geoMercator().fitExtent(
      [
        [10, 10],
        [LARGURA - 10, ALTURA - 10],
      ],
      { type: "FeatureCollection", features: feicoes },
    );
    return geoPath(projecao);
  }, [feicoes]);

  // Zoom e arraste (roda do mouse, arrastar, pinça no celular, duplo clique); reinicia ao trocar de UF.
  useEffect(() => {
    const svg = svgRef.current;
    if (!svg) return;
    const comportamento = zoom<SVGSVGElement, unknown>()
      .scaleExtent([1, ZOOM_MAXIMO])
      .translateExtent([
        [0, 0],
        [LARGURA, ALTURA],
      ])
      .clickDistance(4)
      .on("zoom", (e) => {
        setFoco(null);
        setTransformacao(e.transform);
      });
    zoomRef.current = comportamento;
    const selecao = select(svg);
    selecao.call(comportamento).call(comportamento.transform, zoomIdentity);
    return () => {
      selecao.on(".zoom", null);
    };
  }, [caminho]);

  function aplicarZoom(fator: number | null) {
    const svg = svgRef.current;
    const comportamento = zoomRef.current;
    if (!svg || !comportamento) return;
    const selecao = select(svg).transition().duration(250);
    if (fator === null) comportamento.transform(selecao, zoomIdentity);
    else comportamento.scaleBy(selecao, fator);
  }

  const contagem = useMemo(() => {
    const c: Partial<Record<Status, number>> = {};
    for (const p of ativos.values()) if (estados || !uf || p.uf === uf) c[p.status] = (c[p.status] ?? 0) + 1;
    return c;
  }, [ativos, uf, estados]);

  function cor(p?: PontoMapa): string {
    if (!p) return SEM_EMENDA;
    if (filtro.length && !filtro.includes(p.status)) return FILTRADO;
    return CORES[p.status];
  }

  return (
    <div className={`relative ${painel && selecionado ? "lg:pr-[340px]" : ""}`}>
      <div className="mb-4 flex flex-wrap items-center gap-2">
        <div role="group" aria-label="Camada do mapa" className="flex overflow-hidden rounded-lg border border-borda">
          {(
            [
              ["municipios", "Municípios"],
              ["estados", "Estados e DF"],
            ] as [Camada, string][]
          ).map(([valor, rotulo]) => (
            <button
              key={valor}
              type="button"
              aria-pressed={camada === valor}
              onClick={() => {
                setCamada(valor);
                setSelecionado(null);
              }}
              className={`h-9 px-3 text-sm transition ${
                camada === valor ? "bg-primaria text-white" : "bg-superficie text-apoio hover:text-texto"
              }`}
            >
              {rotulo}
            </button>
          ))}
        </div>
        <select
          hidden={estados}
          value={uf}
          onChange={(e) => setUf(e.target.value)}
          aria-label="Filtrar por UF"
          className="h-9 rounded-lg border border-borda bg-superficie px-3 text-sm text-texto focus:border-primaria"
        >
          <option value="">Brasil</option>
          {UFS.map((u) => (
            <option key={u}>{u}</option>
          ))}
        </select>
        {ORDEM_STATUS.map((s) => (
          <button
            key={s}
            onClick={() => alternarStatus(s)}
            aria-pressed={filtro.includes(s)}
            className={`inline-flex h-9 items-center gap-2 rounded-full border px-3 text-xs transition ${
              filtro.includes(s) ? "border-forte/50 bg-forte/10 text-forte" : "border-borda text-apoio hover:text-texto"
            }`}
          >
            <span className="h-2.5 w-2.5 rounded-sm" style={{ background: CORES[s] }} />
            {ROTULOS[s]} <span className="tabular-nums text-discreto">{numero(contagem[s] ?? 0)}</span>
          </button>
        ))}
      </div>
      {erro && <p className="mb-2 text-sm text-amarelo-claro">{erro}</p>}
      <div className={`relative ${altura}`}>
        {!caminho ? (
          <div className="flex h-[420px] items-center justify-center text-sm text-apoio">Carregando mapa…</div>
        ) : (
          <svg
            ref={svgRef}
            viewBox={`0 0 ${LARGURA} ${ALTURA}`}
            className="mx-auto h-auto max-h-[78vh] w-full cursor-grab touch-none select-none active:cursor-grabbing"
            role="img"
            aria-label="Mapa do Brasil por município. Use a roda do mouse ou os botões para aproximar; arraste para mover."
          >
            <g transform={transformacao.toString()}>
            {feicoes.map((f) => {
              const p = ativos.get(f.properties.c);
              return (
                <path
                  key={f.properties.c}
                  d={caminho(f) ?? undefined}
                  style={{ fill: cor(p), stroke: "var(--t-mapa-borda)" }}
                  strokeWidth={(estados ? 0.9 : uf ? 0.5 : 0.12) / Math.sqrt(transformacao.k)}
                  className="cursor-pointer transition-opacity hover:opacity-70"
                  onMouseMove={(e) => {
                    const r = (e.currentTarget.ownerSVGElement as SVGSVGElement).getBoundingClientRect();
                    setFoco({ ponto: p, codigo: f.properties.c, x: e.clientX - r.left, y: e.clientY - r.top });
                  }}
                  onMouseLeave={() => setFoco(null)}
                  onClick={() => {
                    if (painel && p) setSelecionado(p);
                    else if (p) router.push(destino(p));
                    else if (!estados) router.push(`/municipios/${f.properties.c}`);
                  }}
                />
              );
            })}
            </g>
          </svg>
        )}
        {caminho && (
          <div className="absolute right-2 top-2 flex flex-col overflow-hidden rounded-lg border border-borda bg-lateral/90 shadow-cartao backdrop-blur">
            {BOTOES_ZOOM.map(({ rotulo, icone: Icone, fator }) => (
              <button
                key={rotulo}
                onClick={() => aplicarZoom(fator)}
                title={rotulo}
                aria-label={rotulo}
                className="grid h-9 w-9 place-items-center border-b border-borda/70 text-apoio last:border-b-0 hover:bg-superficie-3 hover:text-forte"
              >
                <Icone className="h-4 w-4" />
              </button>
            ))}
          </div>
        )}
        {caminho && transformacao.k > 1.01 && (
          <p className="pointer-events-none absolute bottom-2 left-2 rounded-md bg-lateral/80 px-2 py-1 text-[11px] tabular-nums text-apoio">
            {transformacao.k.toFixed(1).replace(".", ",")}×
          </p>
        )}
        {foco && (
          <div
            className="pointer-events-none absolute z-10 w-64 rounded-xl border border-borda bg-lateral/95 p-3 text-xs text-texto shadow-suave backdrop-blur"
            style={{ left: Math.min(foco.x + 14, 520), top: foco.y + 14 }}
          >
            {foco.ponto ? (
              <>
                <p className="text-sm font-semibold">
                  {foco.ponto.municipio} · {foco.ponto.uf}
                </p>
                <p className="text-apoio">População {numero(foco.ponto.populacao)}</p>
                <p className="mt-1.5">
                  {foco.ponto.emendas} emenda(s) · {brlCompacto(foco.ponto.repassado)} repassados
                </p>
                <p className="mt-1.5 flex flex-wrap gap-x-2">
                  {ORDEM_STATUS.filter((s) => foco.ponto![s]).map((s) => (
                    <span key={s} style={{ color: CORES_TEXTO[s] }}>
                      {foco.ponto![s]} {s}
                    </span>
                  ))}
                </p>
              </>
            ) : (
              <p className="text-apoio">
                {estados
                  ? `Sem emenda Pix para o governo de ${SIGLA_POR_CODIGO[foco.codigo] ?? foco.codigo} desde 2024.`
                  : `Sem emenda Pix municipal desde 2024 (IBGE ${foco.codigo}).`}
              </p>
            )}
          </div>
        )}
      </div>
      {painel && selecionado && (
        <aside className="cartao mt-4 p-5 lg:absolute lg:right-0 lg:top-0 lg:mt-0 lg:w-[320px]" aria-label="Resumo do município">
          <div className="flex items-start justify-between gap-2">
            <div>
              <p className="text-[11px] uppercase tracking-[0.14em] text-rotulo">{estados ? "Governo estadual" : "Município"} · {selecionado.uf}</p>
              <h3 className="text-xl font-semibold">{selecionado.municipio}</h3>
            </div>
            <button onClick={() => setSelecionado(null)} className="rounded-lg p-1.5 text-apoio hover:bg-superficie-3" aria-label="Fechar painel">
              <X className="h-4 w-4" />
            </button>
          </div>
          <dl className="mt-4 grid grid-cols-2 gap-3 text-sm">
            <div>
              <dt className="text-xs text-discreto">População</dt>
              <dd className="tabular-nums">{numero(selecionado.populacao)}</dd>
            </div>
            <div>
              <dt className="text-xs text-discreto">Repassado</dt>
              <dd className="tabular-nums">{brlCompacto(selecionado.repassado)}</dd>
            </div>
          </dl>
          <ul className="mt-4 space-y-1.5 text-sm">
            {ORDEM_STATUS.map((s) => (
              <li key={s} className="flex items-center justify-between">
                <span className="flex items-center gap-2 text-apoio">
                  <span className="h-2.5 w-2.5 rounded-sm" style={{ background: CORES[s] }} />
                  {ROTULOS[s]}
                </span>
                <span className="tabular-nums" style={{ color: CORES_TEXTO[s] }}>
                  {selecionado[s]}
                </span>
              </li>
            ))}
          </ul>
          <Link
            href={destino(selecionado)}
            className="mt-5 inline-flex w-full items-center justify-center gap-2 rounded-lg bg-primaria px-4 py-2.5 text-sm font-medium text-white shadow-primaria hover:bg-primaria-escura"
          >
            Ver {selecionado.emendas} emenda(s) <ArrowRight className="h-4 w-4" />
          </Link>
        </aside>
      )}
    </div>
  );
}
