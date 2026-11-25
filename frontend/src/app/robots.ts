import type { MetadataRoute } from "next";

/** Robôs podem indexar as páginas, mas não a API (PDFs do dossiê, assistente, contador). */
export default function robots(): MetadataRoute.Robots {
  return { rules: { userAgent: "*", allow: "/", disallow: "/api/" } };
}
