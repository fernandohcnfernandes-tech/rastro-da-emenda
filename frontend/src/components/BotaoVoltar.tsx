"use client";

import { ArrowLeft } from "lucide-react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";

/**
 * Botão "Voltar" exibido no topo do conteúdo quando faz sentido voltar à página anterior:
 * nas fichas (emenda, município, parlamentar) e na lista de emendas aberta já filtrada a partir
 * de outra página (estado, alerta, visão geral). Guarda a trilha de navegação da aba em
 * sessionStorage para saber para onde o "voltar" do navegador leva; sem trilha (link aberto
 * direto), leva à lista correspondente.
 */

const CHAVE = "rastro:trilha";
const LIMITE = 50;

type Destino = { href: string; rotulo: string };

/** Para onde voltar quando a página foi aberta direto, sem histórico no site. */
const RECUO: [RegExp, Destino][] = [
  [/^\/emendas\/\d+/, { href: "/emendas", rotulo: "Emendas" }],
  [/^\/municipios\/\d+/, { href: "/municipios", rotulo: "Municípios" }],
  [/^\/parlamentares\/.+/, { href: "/parlamentares", rotulo: "Parlamentares" }],
];

const NOMES: [RegExp, string][] = [
  [/^\/$/, "Visão geral"],
  [/^\/mapa/, "Mapa"],
  [/^\/emendas\/\d+/, "Ficha da emenda"],
  [/^\/emendas/, "Emendas"],
  [/^\/estados/, "Estados e DF"],
  [/^\/municipios\/\d+/, "Município"],
  [/^\/municipios/, "Municípios"],
  [/^\/parlamentares\/.+/, "Parlamentar"],
  [/^\/parlamentares/, "Parlamentares"],
  [/^\/assistente/, "Pergunte à IA"],
  [/^\/alertas/, "Alertas"],
  [/^\/cobertura/, "Cobertura das fontes"],
  [/^\/como-funciona/, "Como funciona"],
  [/^\/busca/, "Busca"],
];

function nomeDe(url: string): string {
  const caminho = url.split("?")[0];
  return NOMES.find(([r]) => r.test(caminho))?.[1] ?? "página anterior";
}

function caminhoDe(url: string): string {
  return url.split("?")[0];
}

function lerTrilha(): string[] {
  try {
    const t = JSON.parse(sessionStorage.getItem(CHAVE) ?? "[]");
    return Array.isArray(t) ? t.filter((x) => typeof x === "string") : [];
  } catch {
    return [];
  }
}

/** Registra a URL atual: se ela é a penúltima da trilha, foi um "voltar" e a última sai. */
function registrar(url: string): string[] {
  let t = lerTrilha();
  if (t[t.length - 1] === url) return t;
  if (t[t.length - 2] === url) t = t.slice(0, -1);
  else t = [...t, url].slice(-LIMITE);
  try {
    sessionStorage.setItem(CHAVE, JSON.stringify(t));
  } catch {
    /* sessionStorage indisponível: o botão cai no recuo fixo */
  }
  return t;
}

export function BotaoVoltar() {
  const pathname = usePathname();
  const busca = useSearchParams();
  const router = useRouter();
  const consulta = busca.toString();
  const url = consulta ? `${pathname}?${consulta}` : pathname;
  const [anterior, setAnterior] = useState<string | null>(null);

  useEffect(() => {
    const t = registrar(url);
    // eslint-disable-next-line react-hooks/set-state-in-effect -- a trilha vive no sessionStorage, fora do React
    setAnterior(t.length >= 2 ? t[t.length - 2] : null);
  }, [url]);

  const recuo = RECUO.find(([r]) => r.test(pathname))?.[1] ?? null;
  // Lista de emendas filtrada vinda de outra página (ex.: estado, alerta): vale voltar.
  const listaVindaDeFora = pathname === "/emendas" && anterior !== null && caminhoDe(anterior) !== "/emendas";

  if (!recuo && !listaVindaDeFora) return null;

  const rotulo = anterior ? nomeDe(anterior) : recuo!.rotulo;

  function voltar() {
    if (anterior) router.back();
    else router.push(recuo!.href);
  }

  return (
    <button
      type="button"
      onClick={voltar}
      className="mb-5 inline-flex items-center gap-2 rounded-lg border border-borda/70 px-3 py-1.5 text-sm text-apoio transition hover:border-primaria hover:text-texto"
    >
      <ArrowLeft className="h-4 w-4" />
      Voltar{rotulo ? ` para ${rotulo}` : ""}
    </button>
  );
}
