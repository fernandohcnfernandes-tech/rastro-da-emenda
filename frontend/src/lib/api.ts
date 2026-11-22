import "server-only";

/** URL da API lida em tempo de execução (servidor). Em produção: http://api:8000 no docker compose. */
export function urlApi(): string {
  return (process.env.API_URL ?? "http://localhost:8000").replace(/\/$/, "");
}

export class ErroApi extends Error {
  constructor(
    public status: number,
    mensagem: string,
  ) {
    super(mensagem);
  }
}

export async function api<T>(caminho: string): Promise<T> {
  const resp = await fetch(`${urlApi()}${caminho}`, { headers: { Accept: "application/json" } });
  if (!resp.ok) throw new ErroApi(resp.status, `${resp.status} em ${caminho}`);
  return (await resp.json()) as T;
}
