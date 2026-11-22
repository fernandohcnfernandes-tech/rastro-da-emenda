"use client";

import { geoMercator, geoPath } from "d3-geo";
import type { Feature, FeatureCollection, Geometry } from "geojson";
import { ArrowRight, X } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

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
const SEM_EMENDA = "#1a2740";

export function MapaBrasil({ painel = false, altura = "" }: { painel?: boolean; altura?: string }) {
  const router = useRouter();
  const [malha, setMalha] = useState<FeatureCollection<Geometry, { c: string }> | null>(null);
  const [pontos, setPontos] = useState<Map<string, PontoMapa>>(new Map());
  const [uf, setUf] = useState("");
  const [filtro, setFiltro] = useState<Status | "">("");
  const [foco, setFoco] = useState<{ ponto?: PontoMapa; codigo: string; x: number; y: number } | null>(null);
  const [selecionado, setSelecionado] = useState<PontoMapa | null>(null);
  const [erro, setErro] = useState<string | null>(null);

  useEffect(() => {
    fetch("/malha/municipios.json")
      .then((r) => r.json())
      .then(setMalha)
      .catch(() => setErro("Não foi possível carregar a malha do IBGE."));
    fetch("/api/mapa")
      .then((r) => (r.ok ? r.json() : Promise.reject(r.status)))
      .then((lista: PontoMapa[]) => setPontos(new Map(lista.map((p) => [p.codigo_ibge, p]))))
      .catch(() => setErro("API indisponível: o mapa aparece sem cores."));
  }, []);

  const feicoes = useMemo<Municipio[]>(() => {
    if (!malha) return [];
    return uf ? malha.features.filter((f) => f.properties.c.startsWith(PREFIXO_UF[uf])) : malha.features;
  }, [malha, uf]);

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

  const contagem = useMemo(() => {
    const c: Partial<Record<Status, number>> = {};
    for (const p of pontos.values()) if (!uf || p.uf === uf) c[p.status] = (c[p.status] ?? 0) + 1;
    return c;
  }, [pontos, uf]);

  function cor(p?: PontoMapa): string {
    if (!p) return SEM_EMENDA;
    if (filtro && p.status !== filtro) return "#22324f";
    return CORES[p.status];
  }

  return (
    <div className={`relative ${painel && selecionado ? "lg:pr-[340px]" : ""}`}>
      <div className="mb-4 flex flex-wrap items-center gap-2">
        <select
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
            onClick={() => setFiltro(filtro === s ? "" : s)}
            aria-pressed={filtro === s}
            className={`inline-flex h-9 items-center gap-2 rounded-full border px-3 text-xs transition ${
              filtro === s ? "border-white/60 bg-white/10 text-white" : "border-borda text-apoio hover:text-texto"
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
          <svg viewBox={`0 0 ${LARGURA} ${ALTURA}`} className="mx-auto h-auto max-h-[78vh] w-full" role="img" aria-label="Mapa do Brasil por município">
            {feicoes.map((f) => {
              const p = pontos.get(f.properties.c);
              return (
                <path
                  key={f.properties.c}
                  d={caminho(f) ?? undefined}
                  fill={cor(p)}
                  stroke="#05070c"
                  strokeWidth={uf ? 0.5 : 0.12}
                  className="cursor-pointer transition-opacity hover:opacity-70"
                  onMouseMove={(e) => {
                    const r = (e.currentTarget.ownerSVGElement as SVGSVGElement).getBoundingClientRect();
                    setFoco({ ponto: p, codigo: f.properties.c, x: e.clientX - r.left, y: e.clientY - r.top });
                  }}
                  onMouseLeave={() => setFoco(null)}
                  onClick={() => {
                    if (painel && p) setSelecionado(p);
                    else router.push(`/municipios/${f.properties.c}`);
                  }}
                />
              );
            })}
          </svg>
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
              <p className="text-apoio">Sem emenda Pix municipal desde 2024 (IBGE {foco.codigo}).</p>
            )}
          </div>
        )}
      </div>
      {painel && selecionado && (
        <aside className="cartao mt-4 p-5 lg:absolute lg:right-0 lg:top-0 lg:mt-0 lg:w-[320px]" aria-label="Resumo do município">
          <div className="flex items-start justify-between gap-2">
            <div>
              <p className="text-[11px] uppercase tracking-[0.14em] text-rotulo">Município · {selecionado.uf}</p>
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
            href={`/municipios/${selecionado.codigo_ibge}`}
            className="mt-5 inline-flex w-full items-center justify-center gap-2 rounded-lg bg-primaria px-4 py-2.5 text-sm font-medium text-white shadow-primaria hover:bg-primaria-escura"
          >
            Ver {selecionado.emendas} emenda(s) <ArrowRight className="h-4 w-4" />
          </Link>
        </aside>
      )}
    </div>
  );
}
