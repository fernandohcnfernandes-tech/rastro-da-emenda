import type { MetadataRoute } from "next";

/** Robôs de IA e de SEO: proibidos em tudo (o Caddy também os barra pelo User-Agent). */
const ROBOS_BLOQUEADOS = [
  "GPTBot",
  "ChatGPT-User",
  "OAI-SearchBot",
  "ClaudeBot",
  "Claude-User",
  "Claude-SearchBot",
  "anthropic-ai",
  "CCBot",
  "Bytespider",
  "meta-externalagent",
  "Amazonbot",
  "PetalBot",
  "PerplexityBot",
  "Google-Extended",
  "Applebot-Extended",
  "AhrefsBot",
  "SemrushBot",
  "DataForSeoBot",
  "MJ12bot",
  "DotBot",
];

/**
 * Google e Bing indexam as páginas (o site aparece nas buscas), nunca a API (PDFs do dossiê,
 * assistente, contador). Demais robôs, como os de pré-visualização de links, seguem a mesma regra.
 */
export default function robots(): MetadataRoute.Robots {
  return {
    rules: [
      { userAgent: ["Googlebot", "Bingbot"], allow: "/", disallow: "/api/" },
      { userAgent: ROBOS_BLOQUEADOS, disallow: "/" },
      { userAgent: "*", allow: "/", disallow: "/api/" },
    ],
  };
}
