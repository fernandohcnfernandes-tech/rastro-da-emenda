"use client";

import { Bot, Send, Sparkles } from "lucide-react";
import { Fragment, useEffect, useRef, useState } from "react";

type Mensagem = { papel: "usuario" | "assistente"; texto: string };

const SUGESTOES = [
  "Resuma a execução desta emenda.",
  "Os documentos encontrados correspondem ao objeto da emenda?",
  "O que ainda falta para comprovar a execução?",
  "Redija um parágrafo para o dossiê.",
];

/** Texto da IA com **negrito**, listas e links clicáveis — sem HTML bruto. */
function Texto({ conteudo }: { conteudo: string }) {
  const linhas = conteudo.split("\n");
  const inline = (t: string) =>
    t.split(/(https?:\/\/[^\s)]+|\*\*[^*]+\*\*)/g).map((parte, i) => {
      if (/^https?:\/\//.test(parte))
        return (
          <a key={i} href={parte} target="_blank" rel="noreferrer" className="break-all text-destaque underline">
            {parte}
          </a>
        );
      if (/^\*\*.+\*\*$/.test(parte)) return <strong key={i}>{parte.slice(2, -2)}</strong>;
      return <Fragment key={i}>{parte}</Fragment>;
    });
  return (
    <div className="space-y-2 text-sm leading-relaxed">
      {linhas.map((l, i) => {
        const t = l.replace(/^#+\s*/, "").trim();
        if (!t) return null;
        if (/^[-*•]\s+/.test(t)) return <p key={i} className="pl-4 -indent-3">• {inline(t.replace(/^[-*•]\s+/, ""))}</p>;
        return <p key={i}>{inline(t)}</p>;
      })}
    </div>
  );
}

export function Assistente({ idPlano }: { idPlano: number }) {
  const [disponivel, setDisponivel] = useState<boolean | null>(null);
  const [mensagens, setMensagens] = useState<Mensagem[]>([]);
  const [pergunta, setPergunta] = useState("");
  const [enviando, setEnviando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const fim = useRef<HTMLDivElement>(null);

  useEffect(() => {
    fetch("/api/assistente")
      .then((r) => r.json())
      .then((d) => setDisponivel(Boolean(d.disponivel)))
      .catch(() => setDisponivel(false));
  }, []);
  useEffect(() => fim.current?.scrollIntoView({ behavior: "smooth", block: "nearest" }), [mensagens, enviando]);

  async function perguntar(texto: string) {
    const q = texto.trim();
    if (q.length < 3 || enviando) return;
    setErro(null);
    setEnviando(true);
    setPergunta("");
    const historico = mensagens.slice(-8);
    setMensagens((m) => [...m, { papel: "usuario", texto: q }]);
    try {
      const resp = await fetch(`/api/emendas/${idPlano}/assistente`, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ pergunta: q, historico }),
      });
      const dados = await resp.json().catch(() => ({}));
      if (!resp.ok) throw new Error(typeof dados.detail === "string" ? dados.detail : "Não foi possível responder agora.");
      setMensagens((m) => [...m, { papel: "assistente", texto: dados.resposta }]);
    } catch (e) {
      setErro(e instanceof Error ? e.message : "Falha de conexão.");
    } finally {
      setEnviando(false);
    }
  }

  if (disponivel === false)
    return <p className="text-sm text-apoio">O assistente de IA não está disponível neste ambiente.</p>;

  return (
    <div className="cartao flex flex-col p-0">
      <div className="flex items-center gap-2 border-b border-borda/60 px-5 py-3">
        <span className="grid h-8 w-8 place-items-center rounded-lg bg-primaria/15">
          <Sparkles className="h-4 w-4 text-destaque" />
        </span>
        <div>
          <p className="text-sm font-semibold">Assistente de análise</p>
          <p className="text-xs text-discreto">Responde com base nesta ficha e nos documentos coletados. Aponta indícios, não acusa. Confira as fontes.</p>
        </div>
      </div>
      <div className="max-h-[520px] min-h-[220px] space-y-4 overflow-y-auto px-5 py-4" aria-live="polite">
        {mensagens.length === 0 && (
          <div className="flex flex-wrap gap-2">
            {SUGESTOES.map((s) => (
              <button
                key={s}
                type="button"
                onClick={() => perguntar(s)}
                disabled={!disponivel}
                className="rounded-full border border-borda bg-superficie px-3 py-1.5 text-left text-xs text-apoio transition hover:border-destaque hover:text-forte disabled:opacity-50"
              >
                {s}
              </button>
            ))}
          </div>
        )}
        {mensagens.map((m, i) =>
          m.papel === "usuario" ? (
            <div key={i} className="ml-auto max-w-[85%] rounded-2xl rounded-br-sm bg-primaria px-4 py-2 text-sm text-white">
              {m.texto}
            </div>
          ) : (
            <div key={i} className="flex max-w-[95%] gap-3">
              <Bot className="mt-1 h-5 w-5 shrink-0 text-destaque" />
              <div className="rounded-2xl rounded-tl-sm border border-borda/60 bg-superficie-2 px-4 py-3 text-texto">
                <Texto conteudo={m.texto} />
              </div>
            </div>
          ),
        )}
        {enviando && <p className="text-sm text-apoio">Analisando a emenda e os documentos…</p>}
        {erro && <p className="text-sm text-vermelho-claro">{erro}</p>}
        <div ref={fim} />
      </div>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          perguntar(pergunta);
        }}
        className="flex gap-2 border-t border-borda/60 p-3"
      >
        <label htmlFor="pergunta-assistente" className="sr-only">
          Pergunta ao assistente
        </label>
        <input
          id="pergunta-assistente"
          value={pergunta}
          onChange={(e) => setPergunta(e.target.value)}
          maxLength={2000}
          disabled={!disponivel || enviando}
          placeholder="Pergunte sobre a emenda, os contratos ou peça um texto para o dossiê"
          className="h-10 min-w-0 flex-1 rounded-lg border border-borda bg-campo px-3 text-sm placeholder:text-discreto focus:border-primaria focus:outline-none"
        />
        <button
          disabled={!disponivel || enviando || pergunta.trim().length < 3}
          className="grid h-10 w-10 place-items-center rounded-lg bg-primaria text-white shadow-primaria hover:bg-primaria-escura disabled:opacity-50"
          aria-label="Enviar pergunta"
        >
          <Send className="h-4 w-4" />
        </button>
      </form>
    </div>
  );
}
