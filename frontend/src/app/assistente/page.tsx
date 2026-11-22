import { Assistente } from "@/components/Assistente";
import { CabecalhoPagina } from "@/components/ui";

export const metadata = { title: "Pergunte à IA" };

const SUGESTOES = [
  "Quais UFs receberam mais dinheiro em emendas Pix?",
  "Quais parlamentares têm mais valor em emendas com indício para apuração?",
  "Como está a execução das emendas do meu município? (diga o nome)",
  "Quais emendas para compra de ambulâncias têm contrato encontrado?",
  "Quanto das emendas já tem evidência de execução?",
  "Quais fontes já foram coletadas e até quando?",
];

export default function PergunteAIA() {
  return (
    <div className="max-w-5xl">
      <CabecalhoPagina
        rotulo="Análise"
        titulo="Pergunte à IA"
        descricao="Faça perguntas em linguagem natural sobre as emendas Pix, os municípios, os estados, os parlamentares e os contratos que o portal já coletou. A IA consulta o banco do Rastro da Emenda e cita as fichas de onde tirou cada informação."
      />
      <Assistente
        sugestoes={SUGESTOES}
        titulo="Consultor de dados do portal"
        descricao="Responde só com os dados públicos já coletados. Aponta indícios, nunca acusações. A IA pode errar: confira nas fichas."
        placeholder="Ex.: quais municípios do Piauí têm mais emendas sem evidência?"
      />
      <p className="mt-4 text-xs text-discreto">
        Respostas geradas pelo Claude Sonnet 5.5 (Anthropic) a partir do banco do projeto. Limite de 15 perguntas a cada 10 minutos. Não
        informe dados pessoais.
      </p>
    </div>
  );
}
