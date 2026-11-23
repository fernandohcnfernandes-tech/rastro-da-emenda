import type { Status } from "./tipos";

/** Cores sólidas do semáforo (mapa, barras). */
export const CORES: Record<Status, string> = {
  verde: "#16A34A",
  amarelo: "#EAB308",
  laranja: "#EA580C",
  vermelho: "#DC2626",
  azul: "#2563EB",
  cinza: "#94A3B8",
};

/** Variantes claras para texto e selos sobre fundo escuro (contraste AA). */
export const CORES_TEXTO: Record<Status, string> = {
  verde: "var(--t-st-verde)",
  amarelo: "var(--t-st-amarelo)",
  laranja: "var(--t-st-laranja)",
  vermelho: "var(--t-st-vermelho)",
  azul: "var(--t-st-azul)",
  cinza: "var(--t-st-cinza)",
};

export const ROTULOS: Record<Status, string> = {
  verde: "Execução com evidência",
  amarelo: "Evidência parcial",
  laranja: "Em revisão",
  vermelho: "Indício para apuração",
  azul: "Sem evidência localizada",
  cinza: "Dados insuficientes ou em andamento",
};

export const ORDEM_STATUS: Status[] = ["vermelho", "laranja", "amarelo", "verde", "azul", "cinza"];

export function brl(valor: number | null | undefined): string {
  if (valor === null || valor === undefined) return "—";
  return valor.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

export function brlCompacto(valor: number | null | undefined): string {
  if (valor === null || valor === undefined) return "—";
  return valor.toLocaleString("pt-BR", { style: "currency", currency: "BRL", notation: "compact", maximumFractionDigits: 1 });
}

export function data(valor: string | null | undefined): string {
  if (!valor) return "—";
  const [a, m, d] = valor.slice(0, 10).split("-");
  return `${d}/${m}/${a}`;
}

export function numero(valor: number | null | undefined): string {
  return valor === null || valor === undefined ? "—" : valor.toLocaleString("pt-BR");
}

export const NOME_FONTE: Record<string, string> = {
  pncp_contrato: "PNCP · contrato",
  pncp_contratacao: "PNCP · contratação",
  pncp_ata: "PNCP · ata",
  querido_diario: "Querido Diário · diário oficial",
  tce_contrato: "Tribunal de Contas · contrato",
};

export const UFS = "AC AL AM AP BA CE DF ES GO MA MG MS MT PA PB PE PI PR RJ RN RO RR RS SC SE SP TO".split(" ");
