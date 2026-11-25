/** Contador de acessos: a visita é registrada uma vez por sessão do navegador, em qualquer página de entrada. */

export type Acessos = { total: number; hoje: number; desde: string | null };

const CHAVE = "rastro:visita-registrada";
let pendente: Promise<Acessos | null> | null = null;

export function acessos(): Promise<Acessos | null> {
  if (pendente) return pendente;
  let registrada = false;
  try {
    registrada = sessionStorage.getItem(CHAVE) === "1";
  } catch {
    /* sem sessionStorage: só lê o total */
    registrada = true;
  }
  pendente = fetch("/api/acessos", { method: registrada ? "GET" : "POST", cache: "no-store" })
    .then((r) => (r.ok ? (r.json() as Promise<Acessos>) : null))
    .then((dados) => {
      if (dados && !registrada) {
        try {
          sessionStorage.setItem(CHAVE, "1");
        } catch {
          /* ignora */
        }
      }
      return dados;
    })
    .catch(() => null);
  return pendente;
}

/** Depois da primeira leitura, as próximas (ex.: voltar à página inicial) buscam o total atualizado. */
export function esquecerAcessos() {
  pendente = null;
}
