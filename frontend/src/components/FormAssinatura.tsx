"use client";

import { BellRing } from "lucide-react";
import { useState } from "react";

export function FormAssinatura({ tipo, chave, rotulo }: { tipo: "municipio" | "parlamentar"; chave: string; rotulo: string }) {
  const [email, setEmail] = useState("");
  const [mensagem, setMensagem] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  async function enviar(ev: React.FormEvent) {
    ev.preventDefault();
    setEnviando(true);
    setMensagem(null);
    try {
      const resp = await fetch("/api/assinaturas", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ email, tipo, chave }),
      });
      setMensagem(resp.ok ? "Pronto! Avisaremos por e-mail quando algum status mudar." : "Não foi possível registrar. Confira o e-mail.");
    } catch {
      setMensagem("Falha de conexão. Tente de novo.");
    } finally {
      setEnviando(false);
    }
  }

  return (
    <form onSubmit={enviar} className="cartao p-5">
      <div className="mb-3 flex items-center gap-2">
        <span className="grid h-8 w-8 place-items-center rounded-lg bg-primaria/20">
          <BellRing className="h-4 w-4 text-destaque" />
        </span>
        <p className="text-sm font-semibold">Receber alertas</p>
      </div>
      <label htmlFor={`email-${chave}`} className="text-sm text-apoio">
        E-mail quando o semáforo de {rotulo} mudar.
      </label>
      <input
        id={`email-${chave}`}
        type="email"
        required
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        placeholder="seu@email.com"
        className="mt-3 h-10 w-full rounded-lg border border-borda bg-campo px-3 text-sm placeholder:text-discreto focus:border-primaria focus:outline-none"
      />
      <button
        disabled={enviando}
        className="mt-3 h-10 w-full rounded-lg bg-primaria text-sm font-medium text-white shadow-primaria hover:bg-primaria-escura disabled:opacity-60"
      >
        Assinar
      </button>
      {mensagem && <p className="mt-2 text-sm text-apoio">{mensagem}</p>}
    </form>
  );
}
