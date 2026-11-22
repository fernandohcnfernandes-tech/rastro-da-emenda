import Link from "next/link";

export default function NaoEncontrado() {
  return (
    <div className="py-16 text-center">
      <h1 className="text-2xl font-bold">Não encontrado</h1>
      <p className="mt-2 text-slate-600">O registro procurado não existe na base do Rastro da Emenda.</p>
      <Link href="/" className="mt-4 inline-block text-[#2563EB] hover:underline">
        Voltar ao início
      </Link>
    </div>
  );
}
