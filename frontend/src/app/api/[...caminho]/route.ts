/**
 * Proxy para a API FastAPI. Permite que componentes de cliente chamem `/api/...` e que a URL real da API
 * (API_URL) seja definida em tempo de execução, sem rebuild.
 */
const API = () => (process.env.API_URL ?? "http://localhost:8000").replace(/\/$/, "");

async function repassar(req: Request, caminho: string[]): Promise<Response> {
  const origem = new URL(req.url);
  const destino = `${API()}/${caminho.map(encodeURIComponent).join("/")}${origem.search}`;
  const resp = await fetch(destino, {
    method: req.method,
    headers: { "content-type": req.headers.get("content-type") ?? "application/json", accept: "*/*" },
    body: req.method === "POST" ? await req.text() : undefined,
  });
  return new Response(resp.body, {
    status: resp.status,
    headers: { "content-type": resp.headers.get("content-type") ?? "application/json" },
  });
}

export async function GET(req: Request, ctx: { params: Promise<{ caminho: string[] }> }) {
  return repassar(req, (await ctx.params).caminho);
}

export async function POST(req: Request, ctx: { params: Promise<{ caminho: string[] }> }) {
  const { caminho } = await ctx.params;
  if (caminho.join("/") !== "assinaturas") return Response.json({ detail: "não permitido" }, { status: 405 });
  return repassar(req, caminho);
}
