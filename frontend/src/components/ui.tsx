import Link from "next/link";

import { CORES, CORES_TEXTO, ORDEM_STATUS, ROTULOS, numero } from "@/lib/formato";
import type { Status } from "@/lib/tipos";

export function Rotulo({ children }: { children: React.ReactNode }) {
  return <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-rotulo">{children}</p>;
}

export function CabecalhoPagina({
  rotulo,
  titulo,
  descricao,
  acoes,
}: {
  rotulo?: string;
  titulo: React.ReactNode;
  descricao?: React.ReactNode;
  acoes?: React.ReactNode;
}) {
  return (
    <header className="mb-8 flex flex-wrap items-end justify-between gap-4">
      <div className="min-w-0 space-y-2">
        {rotulo && <Rotulo>{rotulo}</Rotulo>}
        <h2 className="text-[28px] font-semibold leading-tight tracking-tight text-texto sm:text-[32px]">{titulo}</h2>
        {descricao && <div className="max-w-3xl text-[15px] leading-relaxed text-apoio">{descricao}</div>}
      </div>
      {acoes && <div className="flex flex-wrap gap-2">{acoes}</div>}
    </header>
  );
}

export function Cartao({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return <section className={`cartao p-5 ${className}`}>{children}</section>;
}

export function TituloCartao({ children, extra }: { children: React.ReactNode; extra?: React.ReactNode }) {
  return (
    <div className="mb-4 flex items-center justify-between gap-3">
      <h3 className="text-[15px] font-semibold text-texto">{children}</h3>
      {extra}
    </div>
  );
}

export function Indicador({
  rotulo,
  valor,
  detalhe,
  icone: Icone,
  tom = "#6f93ff",
  aoClicar,
  ativo = false,
  dica,
}: {
  rotulo: string;
  valor: React.ReactNode;
  detalhe?: React.ReactNode;
  icone?: React.ComponentType<{ className?: string; style?: React.CSSProperties }>;
  tom?: string;
  /** Torna o cartão um botão (ex.: filtrar o mapa). */
  aoClicar?: () => void;
  ativo?: boolean;
  dica?: string;
}) {
  const Elemento = aoClicar ? "button" : "div";
  return (
    <Elemento
      {...(aoClicar ? { onClick: aoClicar, "aria-pressed": ativo, title: dica, type: "button" as const } : {})}
      className={`cartao flex flex-col gap-3 p-5 text-left ${
        aoClicar ? "cursor-pointer transition hover:-translate-y-px hover:border-destaque/60" : ""
      }`}
      style={ativo ? { borderColor: tom, boxShadow: `0 0 0 1px ${tom}, var(--t-sombra-cartao)` } : undefined}
    >
      <div className="flex items-center justify-between">
        <p className="text-[12px] font-medium text-apoio">{rotulo}</p>
        {Icone && (
          <span className="grid h-8 w-8 place-items-center rounded-lg" style={{ background: `${tom}22` }}>
            <Icone className="h-4 w-4" style={{ color: tom }} />
          </span>
        )}
      </div>
      <p className="text-[28px] font-semibold leading-none tracking-tight text-texto tabular-nums">{valor}</p>
      {detalhe && <p className="text-[12px] text-discreto">{detalhe}</p>}
    </Elemento>
  );
}

export function Selo({ status, grande = false }: { status: Status; grande?: boolean }) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border font-medium ${grande ? "px-3.5 py-1.5 text-sm" : "px-2.5 py-0.5 text-xs"}`}
      style={{ color: CORES_TEXTO[status], borderColor: `${CORES[status]}66`, background: `${CORES[status]}1f` }}
      title={ROTULOS[status]}
    >
      <span className="h-1.5 w-1.5 rounded-full" style={{ background: CORES_TEXTO[status] }} aria-hidden />
      {grande ? ROTULOS[status] : status}
    </span>
  );
}

export function BarraSemaforo({
  contagem,
  legenda = true,
  selecionados = [],
  aoSelecionar,
}: {
  contagem: Partial<Record<Status, number>>;
  legenda?: boolean;
  /** Status destacados (os demais ficam esmaecidos). */
  selecionados?: Status[];
  /** Torna a barra e a legenda clicáveis. */
  aoSelecionar?: (s: Status) => void;
}) {
  const total = ORDEM_STATUS.reduce((s, k) => s + (contagem[k] ?? 0), 0);
  const apagado = (s: Status) => selecionados.length > 0 && !selecionados.includes(s);
  return (
    <div>
      <div className="flex h-2.5 w-full overflow-hidden rounded-full bg-superficie-3" role="img" aria-label="Distribuição do semáforo">
        {total > 0 &&
          ORDEM_STATUS.map((s) =>
            contagem[s] ? (
              <div
                key={s}
                onClick={aoSelecionar ? () => aoSelecionar(s) : undefined}
                className={aoSelecionar ? "cursor-pointer transition-opacity" : ""}
                style={{ width: `${(100 * (contagem[s] ?? 0)) / total}%`, background: CORES[s], opacity: apagado(s) ? 0.25 : 1 }}
              />
            ) : null,
          )}
      </div>
      {legenda && (
        <ul className="mt-3 flex flex-wrap gap-x-2 gap-y-1.5 text-[13px]">
          {ORDEM_STATUS.map((s) => {
            const conteudo = (
              <>
                <span className="h-2.5 w-2.5 rounded-sm" style={{ background: CORES[s] }} />
                <span className="font-medium text-texto tabular-nums">{numero(contagem[s] ?? 0)}</span>
                <span className="text-apoio">{ROTULOS[s]}</span>
              </>
            );
            return (
              <li key={s}>
                {aoSelecionar ? (
                  <button
                    type="button"
                    onClick={() => aoSelecionar(s)}
                    aria-pressed={selecionados.includes(s)}
                    className={`flex items-center gap-2 rounded-full border px-2.5 py-1 transition hover:border-destaque/60 ${
                      selecionados.includes(s) ? "border-forte/40 bg-forte/10" : "border-transparent"
                    } ${apagado(s) ? "opacity-50" : ""}`}
                  >
                    {conteudo}
                  </button>
                ) : (
                  <span className="flex items-center gap-2 px-2.5 py-1">{conteudo}</span>
                )}
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}

export function Chip({ href, ativo, children }: { href: string; ativo?: boolean; children: React.ReactNode }) {
  return (
    <Link
      href={href}
      className={`inline-flex min-h-8 items-center gap-1.5 rounded-full border px-3 text-[13px] transition ${
        ativo ? "border-primaria bg-primaria text-white shadow-primaria" : "border-borda bg-superficie text-apoio hover:border-destaque hover:text-texto"
      }`}
    >
      {children}
    </Link>
  );
}

export function BotaoLink({
  href,
  children,
  primario = false,
  externo = false,
}: {
  href: string;
  children: React.ReactNode;
  primario?: boolean;
  externo?: boolean;
}) {
  const classe = `inline-flex min-h-10 items-center gap-2 rounded-lg border px-4 text-sm font-medium transition ${
    primario
      ? "border-primaria bg-primaria text-white shadow-primaria hover:bg-primaria-escura"
      : "border-borda bg-superficie-2 text-cinza-claro hover:border-primaria hover:text-forte"
  }`;
  return externo ? (
    <a href={href} className={classe} target="_blank" rel="noreferrer nofollow">
      {children}
    </a>
  ) : (
    <Link href={href} className={classe}>
      {children}
    </Link>
  );
}

export function Vazio({ children }: { children: React.ReactNode }) {
  return <p className="rounded-lg border border-dashed border-borda px-4 py-8 text-center text-sm text-apoio">{children}</p>;
}

export function Aviso({ children, tom = "vermelho" }: { children: React.ReactNode; tom?: Status }) {
  return (
    <div className="rounded-xl border px-4 py-3 text-sm leading-relaxed" style={{ borderColor: `${CORES[tom]}55`, background: `${CORES[tom]}14`, color: CORES_TEXTO[tom] }}>
      {children}
    </div>
  );
}

export function Paginacao({ pagina, total, tamanho, link }: { pagina: number; total: number; tamanho: number; link: (p: number) => string }) {
  const paginas = Math.max(1, Math.ceil(total / tamanho));
  if (paginas <= 1) return null;
  return (
    <nav className="mt-4 flex items-center justify-between text-sm text-apoio" aria-label="Paginação">
      {pagina > 1 ? (
        <Link href={link(pagina - 1)} className="rounded-lg border border-borda px-3 py-1.5 hover:border-primaria hover:text-texto">
          ← Anterior
        </Link>
      ) : (
        <span />
      )}
      <span className="tabular-nums">
        Página {numero(pagina)} de {numero(paginas)}
      </span>
      {pagina < paginas ? (
        <Link href={link(pagina + 1)} className="rounded-lg border border-borda px-3 py-1.5 hover:border-primaria hover:text-texto">
          Próxima →
        </Link>
      ) : (
        <span />
      )}
    </nav>
  );
}

export function ErroApi() {
  return <Aviso tom="amarelo">A API está indisponível no momento. Tente novamente em instantes.</Aviso>;
}
