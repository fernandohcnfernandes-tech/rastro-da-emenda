"use client";

import {
  AlertTriangle,
  MessageSquareText,
  BookOpen,
  Building2,
  ChevronsLeft,
  ChevronsRight,
  FileText,
  Landmark,
  LayoutDashboard,
  Map as MapaIcone,
  Menu,
  Search,
  ShieldCheck,
  Users,
  X,
} from "lucide-react";
import Link from "next/link";

import { acessos } from "@/lib/acessos";

import { BotaoVoltar } from "./BotaoVoltar";
import { SeletorTema } from "./SeletorTema";
import { usePathname, useRouter } from "next/navigation";
import { Suspense, useEffect, useRef, useState, useSyncExternalStore } from "react";

type Item = { href: string; rotulo: string; icone: React.ComponentType<{ className?: string }> };

const GRUPOS: { titulo: string; itens: Item[] }[] = [
  {
    titulo: "Explorar",
    itens: [
      { href: "/", rotulo: "Visão geral", icone: LayoutDashboard },
      { href: "/mapa", rotulo: "Mapa", icone: MapaIcone },
      { href: "/emendas", rotulo: "Emendas", icone: FileText },
      { href: "/estados", rotulo: "Estados e DF", icone: Building2 },
      { href: "/municipios", rotulo: "Municípios", icone: Landmark },
      { href: "/parlamentares", rotulo: "Parlamentares", icone: Users },
    ],
  },
  {
    titulo: "Análise",
    itens: [
      { href: "/assistente", rotulo: "Pergunte à IA", icone: MessageSquareText },
      { href: "/alertas", rotulo: "Alertas", icone: AlertTriangle },
      { href: "/cobertura", rotulo: "Cobertura das fontes", icone: ShieldCheck },
    ],
  },
  { titulo: "Sobre", itens: [{ href: "/como-funciona", rotulo: "Como funciona", icone: BookOpen }] },
];

const TITULOS: [RegExp, string][] = [
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
];

const CHAVE = "rastro:menu-recolhido";
const EVENTO = "rastro:menu";

function assinarMenu(aviso: () => void) {
  window.addEventListener("storage", aviso);
  window.addEventListener(EVENTO, aviso);
  return () => {
    window.removeEventListener("storage", aviso);
    window.removeEventListener(EVENTO, aviso);
  };
}

function useMenuRecolhido(): [boolean, () => void] {
  const recolhido = useSyncExternalStore(
    assinarMenu,
    () => localStorage.getItem(CHAVE) === "1",
    () => false,
  );
  const alternar = () => {
    localStorage.setItem(CHAVE, recolhido ? "0" : "1");
    window.dispatchEvent(new Event(EVENTO));
  };
  return [recolhido, alternar];
}

function TituloPagina() {
  const pathname = usePathname();
  return <>{TITULOS.find(([r]) => r.test(pathname))?.[1] ?? "Rastro da Emenda"}</>;
}

function ItensMenu({ estreito, aoNavegar }: { estreito: boolean; aoNavegar: () => void }) {
  const pathname = usePathname();
  return (
    <>
      {GRUPOS.map((g) => (
        <div key={g.titulo}>
          {estreito ? (
            <div className="mx-3 mb-2 border-t border-borda/60" />
          ) : (
            <p className="mb-1.5 px-3 text-[10px] font-semibold uppercase tracking-[0.12em] text-discreto">{g.titulo}</p>
          )}
          <ul className="space-y-0.5">
            {g.itens.map(({ href, rotulo, icone: Icone }) => {
              const atual = ativo(pathname, href);
              return (
                <li key={href}>
                  <Link
                    href={href}
                    onClick={aoNavegar}
                    aria-current={atual ? "page" : undefined}
                    title={estreito ? rotulo : undefined}
                    className={`flex min-h-[42px] items-center gap-3 rounded-lg border px-3 text-[14px] transition ${
                      estreito ? "justify-center" : ""
                    } ${
                      atual
                        ? "border-destaque/40 bg-gradient-to-r from-primaria/30 to-primaria-escura/10 text-forte shadow-[inset_3px_0_0_var(--t-destaque)]"
                        : "border-transparent text-apoio hover:border-destaque/20 hover:bg-primaria/10 hover:text-texto"
                    }`}
                  >
                    <Icone className="h-[18px] w-[18px] shrink-0" />
                    {!estreito && <span className="truncate">{rotulo}</span>}
                  </Link>
                </li>
              );
            })}
          </ul>
        </div>
      ))}
    </>
  );
}

function ativo(pathname: string, href: string): boolean {
  return href === "/" ? pathname === "/" : pathname === href || pathname.startsWith(`${href}/`);
}

export function AppShell({ children, rodape }: { children: React.ReactNode; rodape: React.ReactNode }) {
  const router = useRouter();
  const [recolhido, alternar] = useMenuRecolhido();
  const [gaveta, setGaveta] = useState(false);
  const busca = useRef<HTMLInputElement>(null);

  // Conta a visita uma vez por sessão, seja qual for a página de entrada.
  useEffect(() => {
    void acessos();
  }, []);

  useEffect(() => {
    function atalho(e: KeyboardEvent) {
      const alvo = e.target as HTMLElement;
      if (e.key === "/" && !["INPUT", "TEXTAREA", "SELECT"].includes(alvo.tagName)) {
        e.preventDefault();
        busca.current?.focus();
      }
    }
    window.addEventListener("keydown", atalho);
    return () => window.removeEventListener("keydown", atalho);
  }, []);

  function buscar(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const q = new FormData(e.currentTarget).get("q")?.toString().trim();
    router.push(q ? `/emendas?q=${encodeURIComponent(q)}` : "/emendas");
  }

  const estreito = recolhido && !gaveta;

  const menu = (
    <nav aria-label="Navegação principal" className="flex h-full flex-col">
      <div className={`mb-6 flex items-start ${estreito ? "justify-center" : "justify-between"} gap-2 px-2`}>
        <Link href="/" className="block" aria-label="Rastro da Emenda — início">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src="/marca/qkvworks-logo-negativo.svg"
            alt="QKV works"
            className={`claro:hidden ${estreito ? "h-10 w-10 object-cover object-left" : "h-9 w-auto"}`}
          />
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src="/marca/qkvworks-logo-positivo.svg"
            alt="QKV works"
            className={`hidden claro:block ${estreito ? "h-10 w-10 object-cover object-left" : "h-9 w-auto"}`}
          />
          {!estreito && (
            <span className="mt-3 block text-[15px] font-semibold tracking-tight text-texto">Rastro da Emenda</span>
          )}
        </Link>
        {gaveta && (
          <button onClick={() => setGaveta(false)} className="rounded-lg p-2 text-apoio hover:bg-superficie-2" aria-label="Fechar menu">
            <X className="h-5 w-5" />
          </button>
        )}
      </div>
      <div className="flex-1 space-y-5 overflow-y-auto">
        <Suspense fallback={null}>
          <ItensMenu estreito={estreito} aoNavegar={() => setGaveta(false)} />
        </Suspense>
      </div>
      <div className="mt-4 border-t border-borda/60 pt-4">
        {!estreito && (
          <div className="space-y-2 px-3 text-[11px] leading-relaxed text-discreto">
            <p>O sistema aponta indícios para apuração, nunca acusações.</p>
            {rodape}
          </div>
        )}
        <button
          onClick={alternar}
          className="mt-3 hidden w-full items-center justify-center gap-2 rounded-lg border border-borda/60 py-2 text-xs text-apoio hover:border-primaria hover:text-texto lg:flex"
          aria-label={recolhido ? "Expandir menu" : "Recolher menu"}
        >
          {recolhido ? <ChevronsRight className="h-4 w-4" /> : <><ChevronsLeft className="h-4 w-4" /> Recolher</>}
        </button>
      </div>
    </nav>
  );

  return (
    <div className={`grid min-h-screen grid-cols-1 ${recolhido ? "lg:grid-cols-[84px_minmax(0,1fr)]" : "lg:grid-cols-[264px_minmax(0,1fr)]"}`}>
      <aside className="sticky top-0 hidden h-screen border-r border-apoio/15 bg-lateral px-3 py-5 shadow-lateral lg:block">
        {menu}
      </aside>
      {gaveta && (
        <div className="fixed inset-0 z-40 lg:hidden" role="dialog" aria-modal="true">
          <div className="absolute inset-0 bg-black/60" onClick={() => setGaveta(false)} />
          <aside className="absolute inset-y-0 left-0 w-72 border-r border-borda bg-lateral px-3 py-5">{menu}</aside>
        </div>
      )}
      <div className="fundo-app flex min-w-0 flex-col">
        <header className="sticky top-0 z-30 flex items-center gap-3 border-b border-apoio/15 bg-lateral/85 px-4 py-3 backdrop-blur-xl sm:px-8">
          <button onClick={() => setGaveta(true)} className="rounded-lg p-2 text-apoio hover:bg-superficie-2 lg:hidden" aria-label="Abrir menu">
            <Menu className="h-5 w-5" />
          </button>
          <h1 className="hidden text-[15px] font-semibold text-texto sm:block">
            <Suspense fallback="Rastro da Emenda">
              <TituloPagina />
            </Suspense>
          </h1>
          <form onSubmit={buscar} role="search" className="ml-auto flex w-full max-w-md items-center">
            <label className="relative w-full">
              <span className="sr-only">Buscar</span>
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-discreto" />
              <input
                ref={busca}
                name="q"
                placeholder="Buscar emenda, município, parlamentar…"
                className="h-10 w-full rounded-lg border border-borda bg-campo pl-9 pr-10 text-sm text-texto placeholder:text-discreto focus:border-primaria focus:outline-none"
              />
              <kbd className="absolute right-3 top-1/2 hidden -translate-y-1/2 rounded border border-borda px-1.5 text-[10px] text-discreto sm:block">/</kbd>
            </label>
          </form>
          <SeletorTema />
        </header>
        <main className="mx-auto w-full max-w-7xl flex-1 px-4 py-8 sm:px-8">
          <Suspense fallback={null}>
            <BotaoVoltar />
          </Suspense>
          {children}
        </main>
      </div>
    </div>
  );
}
