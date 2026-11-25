import { type NextRequest, NextResponse } from "next/server";

/**
 * Limite de pedidos por IP (25/11/2026), contra robôs que se passam por navegador.
 * Janela fixa de 1 minuto, em memória (o site roda num único processo). O IP vem do Caddy
 * (X-Forwarded-For posto por ele, sem confiar no que o cliente manda). Quem passa do limite
 * recebe 429; insistir leva ao banimento pelo fail2ban, que lê o log do Caddy.
 */

type Tipo = "api" | "pagina";

const LIMITES: Record<Tipo, number> = {
  api: 60, // chamadas à API por minuto
  // Páginas por minuto, incluindo navegação interna e pré-carregamento de links (uma lista dispara
  // dezenas). O Next remove os sinais de pré-carregamento antes daqui; a regra fina, só para páginas
  // completas, fica no fail2ban, que lê esses cabeçalhos no log do Caddy.
  pagina: 600,
};

const JANELA_MS = 60_000;
const MAX_CHAVES = 50_000;
const contagem = new Map<string, { inicio: number; n: number }>();

function tipoDe(req: NextRequest): Tipo {
  return req.nextUrl.pathname.startsWith("/api/") ? "api" : "pagina";
}

function ipDe(req: NextRequest): string {
  return (req.headers.get("x-forwarded-for") ?? "").split(",")[0].trim() || "desconhecido";
}

function limpar(agora: number) {
  for (const [chave, v] of contagem) if (agora - v.inicio >= JANELA_MS) contagem.delete(chave);
}

export function proxy(req: NextRequest) {
  const tipo = tipoDe(req);
  const chave = `${ipDe(req)}|${tipo}`;
  const agora = Date.now();
  if (contagem.size > MAX_CHAVES) limpar(agora);
  const atual = contagem.get(chave);
  if (!atual || agora - atual.inicio >= JANELA_MS) {
    contagem.set(chave, { inicio: agora, n: 1 });
    return NextResponse.next();
  }
  atual.n += 1;
  if (atual.n > LIMITES[tipo]) {
    const espera = Math.ceil((atual.inicio + JANELA_MS - agora) / 1000);
    return new NextResponse("Muitos acessos em pouco tempo. Tente de novo em instantes.", {
      status: 429,
      headers: { "retry-after": String(espera), "content-type": "text/plain; charset=utf-8" },
    });
  }
  return NextResponse.next();
}

export const config = {
  // Fora: arquivos estáticos, imagens, malha do mapa, marca e robots.txt.
  matcher: ["/((?!_next/|marca/|malha/|favicon|icon|apple-icon|robots.txt|sitemap).*)"],
};
