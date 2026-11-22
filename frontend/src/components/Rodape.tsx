import { api } from "@/lib/api";

interface Atualizacao {
  ultimo_job: { tipo: string; fim: string } | null;
  ultima_avaliacao: string | null;
}

export async function Rodape() {
  let texto = "indisponível";
  try {
    const a = await api<Atualizacao>("/atualizacao");
    const quando = a.ultima_avaliacao ?? a.ultimo_job?.fim;
    if (quando) texto = new Date(quando).toLocaleString("pt-BR", { timeZone: "America/Sao_Paulo", dateStyle: "short", timeStyle: "short" });
  } catch {
    /* API fora do ar: rodapé mostra "indisponível" */
  }
  return <p className="whitespace-nowrap">Última atualização dos dados: {texto}</p>;
}
