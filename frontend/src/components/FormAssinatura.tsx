"use client";

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
    <form onSubmit={enviar} className="rounded-lg border border-slate-200 bg-slate-50 p-4">
      <label htmlFor={`email-${chave}`} className="text-sm font-semibold text-[#0B0F1A]">
        Receber alertas sobre {rotulo}
      </label>
      <div className="mt-2 flex gap-2">
        <input
          id={`email-${chave}`}
          type="email"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="seu@email.com"
          className="min-w-0 flex-1 rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-[#2563EB] focus:outline-none"
        />
        <button disabled={enviando} className="rounded-md bg-[#2563EB] px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-60">
          Assinar
        </button>
      </div>
      {mensagem && <p className="mt-2 text-sm text-slate-600">{mensagem}</p>}
    </form>
  );
}
