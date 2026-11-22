"use client";

import { geoMercator, geoPath } from "d3-geo";
import type { Feature, FeatureCollection, Geometry } from "geojson";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import { CORES, ORDEM_STATUS, ROTULOS, brlCompacto, numero } from "@/lib/formato";
import type { PontoMapa } from "@/lib/tipos";

type Municipio = Feature<Geometry, { c: string }>;

const LARGURA = 800;
const ALTURA = 780;
const UFS = "AC AL AM AP BA CE DF ES GO MA MG MS MT PA PB PE PI PR RJ RN RO RR RS SC SE SP TO".split(" ");
const PREFIXO_UF: Record<string, string> = {
  RO: "11", AC: "12", AM: "13", RR: "14", PA: "15", AP: "16", TO: "17", MA: "21", PI: "22", CE: "23", RN: "24",
  PB: "25", PE: "26", AL: "27", SE: "28", BA: "29", MG: "31", ES: "32", RJ: "33", SP: "35", PR: "41", SC: "42",
  RS: "43", MS: "50", MT: "51", GO: "52", DF: "53",
};

export function MapaBrasil() {
  const router = useRouter();
  const [malha, setMalha] = useState<FeatureCollection<Geometry, { c: string }> | null>(null);
  const [pontos, setPontos] = useState<Map<string, PontoMapa>>(new Map());
  const [uf, setUf] = useState("");
  const [foco, setFoco] = useState<{ ponto?: PontoMapa; codigo: string; x: number; y: number } | null>(null);
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
        [8, 8],
        [LARGURA - 8, ALTURA - 8],
      ],
      { type: "FeatureCollection", features: feicoes },
    );
    return geoPath(projecao);
  }, [feicoes]);

  const contagem = useMemo(() => {
    const c: Record<string, number> = {};
    for (const p of pontos.values()) if (!uf || p.uf === uf) c[p.status] = (c[p.status] ?? 0) + 1;
    return c;
  }, [pontos, uf]);

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-bold text-[#0B0F1A]">Mapa do semáforo por município</h2>
          <p className="text-xs text-slate-500">Vermelho se houver ao menos uma emenda com indício; senão, a cor da maioria. Clique para abrir o município.</p>
        </div>
        <label className="text-sm text-slate-600">
          UF{" "}
          <select value={uf} onChange={(e) => setUf(e.target.value)} className="ml-1 rounded-md border border-slate-300 px-2 py-1">
            <option value="">Brasil</option>
            {UFS.map((u) => (
              <option key={u}>{u}</option>
            ))}
          </select>
        </label>
      </div>
      {erro && <p className="mb-2 text-sm text-amber-700">{erro}</p>}
      <div className="relative">
        {!caminho ? (
          <div className="flex h-[480px] items-center justify-center text-sm text-slate-500">Carregando mapa…</div>
        ) : (
          <svg viewBox={`0 0 ${LARGURA} ${ALTURA}`} className="h-auto w-full" role="img" aria-label="Mapa do Brasil por município">
            {feicoes.map((f) => {
              const p = pontos.get(f.properties.c);
              return (
                <path
                  key={f.properties.c}
                  d={caminho(f) ?? undefined}
                  fill={p ? CORES[p.status] : "#E2E8F0"}
                  stroke="#ffffff"
                  strokeWidth={uf ? 0.6 : 0.15}
                  className="cursor-pointer transition-opacity hover:opacity-70"
                  onMouseMove={(e) => {
                    const r = (e.currentTarget.ownerSVGElement as SVGSVGElement).getBoundingClientRect();
                    setFoco({ ponto: p, codigo: f.properties.c, x: e.clientX - r.left, y: e.clientY - r.top });
                  }}
                  onMouseLeave={() => setFoco(null)}
                  onClick={() => router.push(`/municipios/${f.properties.c}`)}
                />
              );
            })}
          </svg>
        )}
        {foco && (
          <div
            className="pointer-events-none absolute z-10 w-60 rounded-md bg-[#0B0F1A] p-3 text-xs text-white shadow-lg"
            style={{ left: Math.min(foco.x + 12, LARGURA - 260), top: foco.y + 12 }}
          >
            {foco.ponto ? (
              <>
                <p className="text-sm font-bold">
                  {foco.ponto.municipio} · {foco.ponto.uf}
                </p>
                <p className="text-slate-300">População: {numero(foco.ponto.populacao)}</p>
                <p className="mt-1">
                  {foco.ponto.emendas} emenda(s) · {brlCompacto(foco.ponto.repassado)} repassados
                </p>
                <p className="mt-1">
                  {ORDEM_STATUS.filter((s) => foco.ponto![s]).map((s) => `${foco.ponto![s]} ${s}`).join(" · ")}
                </p>
              </>
            ) : (
              <p>Sem emenda Pix municipal desde 2024 (IBGE {foco.codigo}).</p>
            )}
          </div>
        )}
      </div>
      <ul className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-xs">
        {ORDEM_STATUS.map((s) => (
          <li key={s} className="flex items-center gap-1.5">
            <span className="h-3 w-3 rounded-sm" style={{ backgroundColor: CORES[s] }} />
            {ROTULOS[s]} <span className="text-slate-500">({numero(contagem[s] ?? 0)})</span>
          </li>
        ))}
        <li className="flex items-center gap-1.5">
          <span className="h-3 w-3 rounded-sm bg-slate-200" /> Sem emenda municipal
        </li>
      </ul>
    </div>
  );
}
