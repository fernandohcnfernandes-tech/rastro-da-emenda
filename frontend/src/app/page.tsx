import Link from "next/link";
import { Suspense } from "react";

import { PainelVisaoGeral } from "@/components/PainelVisaoGeral";
import { BotaoLink, Cartao, ErroApi, Rotulo, TituloCartao } from "@/components/ui";
import { api } from "@/lib/api";
import { CORES, ORDEM_STATUS, brlCompacto, numero } from "@/lib/formato";
import type { Resumo } from "@/lib/tipos";

async function Painel() {
  let r: Resumo;
  try {
    r = await api<Resumo>("/resumo");
  } catch {
    return <ErroApi />;
  }
  const maiorUf = Math.max(1, ...r.por_uf.map((u) => u.emendas));
  return (
    <div className="space-y-6">
      <PainelVisaoGeral
        resumo={r}
        lateral={
          <>
          <Cartao>
            <TituloCartao extra={<Link href="/emendas?status=vermelho" className="text-xs text-destaque hover:underline">ver todas</Link>}>
              Mais valor com indício
            </TituloCartao>
            <ol className="space-y-1">
              {r.ranking_indicios.map((m, i) => (
                <li key={m.codigo_ibge}>
                  <Link href={`/municipios/${m.codigo_ibge}`} className="flex items-center gap-3 rounded-lg px-2 py-2 transition hover:bg-superficie-3/70">
                    <span className="w-5 text-right text-xs tabular-nums text-discreto">{i + 1}</span>
                    <span className="min-w-0 flex-1">
                      <span className="block truncate text-sm text-texto">{m.municipio}</span>
                      <span className="text-xs text-discreto">
                        {m.uf} · {m.vermelhas} emenda(s)
                      </span>
                    </span>
                    <span className="text-sm tabular-nums text-vermelho-claro">{brlCompacto(m.repassado_vermelho)}</span>
                  </Link>
                </li>
              ))}
            </ol>
          </Cartao>
          <Cartao>
            <Rotulo>Aviso</Rotulo>
            <p className="mt-2 text-sm leading-relaxed text-apoio">
              Vermelho é indício para apuração, nunca acusação. Azul significa que não há fonte pública para verificar.
            </p>
            <Link href="/como-funciona" className="mt-3 inline-block text-sm text-destaque hover:underline">
              Entenda as regras →
            </Link>
          </Cartao>
          </>
        }
      />

      <Cartao>
        <TituloCartao>Emendas por UF</TituloCartao>
        <ul className="grid gap-x-8 gap-y-2 md:grid-cols-2">
          {r.por_uf.map((u) => (
            <li key={u.uf} className="flex items-center gap-3 text-sm">
              <Link href={`/emendas?uf=${u.uf}`} className="w-7 font-medium text-cinza-claro hover:text-forte">
                {u.uf}
              </Link>
              <div className="flex h-2 flex-1 overflow-hidden rounded-full bg-superficie-3">
                <div className="flex h-full" style={{ width: `${(100 * u.emendas) / maiorUf}%` }}>
                  {ORDEM_STATUS.map((s) => (u[s] ? <div key={s} style={{ flex: u[s], background: CORES[s] }} /> : null))}
                </div>
              </div>
              <span className="w-14 text-right tabular-nums text-discreto">{numero(u.emendas)}</span>
            </li>
          ))}
        </ul>
      </Cartao>
    </div>
  );
}

export default function VisaoGeral() {
  return (
    <>
      <section className="mb-8 overflow-hidden rounded-2xl border border-borda/70 heroi px-6 py-9 sm:px-10">
        <Rotulo>Emendas Pix · 2024 até hoje</Rotulo>
        <h2 className="mt-3 max-w-3xl text-3xl font-semibold leading-tight tracking-tight sm:text-[40px]">
          Segue cada real da emenda parlamentar até o contrato no município — e avisa quando o rastro some.
        </h2>
        <p className="mt-4 max-w-2xl text-[15px] leading-relaxed text-apoio">
          Cruzamos Transferegov, Portal da Transparência, PNCP, Tribunais de Contas e diários oficiais para mostrar, emenda por emenda, se há evidência
          de que o dinheiro virou licitação e contrato.
        </p>
        <div className="mt-6 flex flex-wrap gap-2">
          <BotaoLink href="/emendas" primario>
            Explorar emendas
          </BotaoLink>
          <BotaoLink href="/mapa">Ver o mapa</BotaoLink>
        </div>
      </section>
      <Suspense fallback={<p className="text-sm text-apoio">Carregando indicadores…</p>}>
        <Painel />
      </Suspense>
    </>
  );
}
