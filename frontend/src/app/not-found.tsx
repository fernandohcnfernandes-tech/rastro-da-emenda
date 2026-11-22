import { BotaoLink, Rotulo } from "@/components/ui";

export default function NaoEncontrado() {
  return (
    <div className="py-20 text-center">
      <Rotulo>Erro 404</Rotulo>
      <h2 className="mt-3 text-2xl font-semibold">Não encontrado</h2>
      <p className="mt-2 text-apoio">O registro procurado não existe na base do Rastro da Emenda.</p>
      <div className="mt-6 flex justify-center">
        <BotaoLink href="/" primario>
          Voltar à visão geral
        </BotaoLink>
      </div>
    </div>
  );
}
