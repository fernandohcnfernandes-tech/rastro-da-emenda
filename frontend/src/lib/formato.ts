import type { Status } from "./tipos";

export const CORES: Record<Status, string> = {
  verde: "#16A34A",
  amarelo: "#EAB308",
  vermelho: "#DC2626",
  azul: "#2563EB",
  cinza: "#94A3B8",
};

export const ROTULOS: Record<Status, string> = {
  verde: "Execução com evidência",
  amarelo: "Evidência parcial",
  vermelho: "Indício para apuração",
  azul: "Sem fonte para verificar",
  cinza: "Dados insuficientes ou dentro do prazo",
};

export const ORDEM_STATUS: Status[] = ["vermelho", "amarelo", "verde", "azul", "cinza"];

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
};
