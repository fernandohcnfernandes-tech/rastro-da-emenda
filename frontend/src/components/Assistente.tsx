"use client";

import { Bot, Send, Sparkles } from "lucide-react";
import { Fragment, useEffect, useRef, useState } from "react";

type Mensagem = { papel: "usuario" | "assistente"; texto: string };

const SUGESTOES_EMENDA = [
  "Resuma a execução desta emenda.",
  "Os documentos encontrados correspondem ao objeto da emenda?",
  "O que ainda falta para comprovar a execução?",
  "Redija um parágrafo para o dossiê.",
];

const LINK = "break-all text-destaque underline";

/** Negrito, links markdown e URLs soltas — sem HTML bruto. Links só http(s). */
function inline(t: string) {
  return t.split(/(\[[^\]]+\]\(https?:\/\/[^\s)]+\)|https?:\/\/[^\s)|]+|\*\*[^*]+\*\*)/g).map((parte, i) => {
    const md = parte.match(/^\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)$/);
    if (md)
      return (
        <a key={i} href={md[2]} target="_blank" rel="noreferrer" className={LINK}>
          {md[1].replace(/\*\*/g, "")}
        </a>
      );
    if (/^https?:\/\//.test(parte))
      return (
        <a key={i} href={parte} target="_blank" rel="noreferrer" className={LINK}>
          {parte}
        </a>
      );
    if (/^\*\*.+\*\*$/.test(parte)) return <strong key={i}>{inline(parte.slice(2, -2))}</strong>;
    return <Fragment key={i}>{parte}</Fragment>;
  });
}

const celulas = (linha: string) => linha.trim().replace(/^\|/, "").replace(/\|$/, "").split("|").map((c) => c.trim());

/** Texto da IA: parágrafos, títulos, listas e tabelas markdown. */
function Texto({ conteudo }: { conteudo: string }) {
  const linhas = conteudo.split("\n");
  const blocos: React.ReactNode[] = [];
  for (let i = 0; i < linhas.length; i++) {
    const bruta = linhas[i].trim();
    if (bruta.startsWith("|")) {
      const tabela: string[] = [];
      while (i < linhas.length && linhas[i].trim().startsWith("|")) tabela.push(linhas[i++].trim());
      i--;
      const [cab, ...resto] = tabela;
      const corpo = resto.filter((l) => !/^\|[\s:|-]+\|?$/.test(l));
      blocos.push(
        <div key={i} className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-borda">
                {celulas(cab).map((c, j) => (
                  <th key={j} className="px-2 py-1.5 font-semibold text-forte">
                    {inline(c)}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {corpo.map((l, k) => (
                <tr key={k} className="border-b border-borda/50">
                  {celulas(l).map((c, j) => (
                    <td key={j} className="px-2 py-1.5 align-top">
                      {inline(c)}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>,
      );
      continue;
    }
    const titulo = /^#+\s+/.test(bruta);
    const t = bruta.replace(/^#+\s*/, "");
    if (!t || /^-{3,}$/.test(t)) continue;
    if (/^([-*•]|\d+[.)])\s+/.test(t)) {
      const marcador = t.match(/^(\d+[.)])/)?.[1] ?? "•";
      blocos.push(
        <p key={i} className="pl-4 -indent-3">
          {marcador} {inline(t.replace(/^([-*•]|\d+[.)])\s+/, ""))}
        </p>,
      );
    } else blocos.push(<p key={i} className={titulo ? "pt-1 font-semibold text-forte" : undefined}>{inline(t)}</p>);
  }
  return <div className="space-y-2 text-sm leading-relaxed">{blocos}</div>;
}

type Props = {
  /** Emenda em análise; sem ela, o chat consulta os dados do portal como um todo. */
  idPlano?: number;
  sugestoes?: string[];
  titulo?: string;
  descricao?: string;
  placeholder?: string;
};

export function Assistente({
  idPlano,
  sugestoes = SUGESTOES_EMENDA,
  titulo = "Assistente de análise",
  descricao = "Responde com base nesta ficha e nos documentos coletados. Aponta indícios, não acusa. Confira as fontes.",
  placeholder = "Pergunte sobre a emenda, os contratos ou peça um texto para o dossiê",
}: Props) {
  const endpoint = idPlano ? `/api/emendas/${idPlano}/assistente` : "/api/assistente/perguntar";
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
  // corpo entre chaves: o Chrome recente devolve uma Promise em scrollIntoView, e o React a trataria como limpeza
  useEffect(() => {
    fim.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }, [mensagens, enviando]);

  async function perguntar(texto: string) {
    const q = texto.trim();
    if (q.length < 3 || enviando) return;
    setErro(null);
    setEnviando(true);
    setPergunta("");
    const historico = mensagens.slice(-8);
    setMensagens((m) => [...m, { papel: "usuario", texto: q }]);
    try {
      const resp = await fetch(endpoint, {
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
          <p className="text-sm font-semibold">{titulo}</p>
          <p className="text-xs text-discreto">{descricao}</p>
        </div>
      </div>
      <div className="max-h-[520px] min-h-[220px] space-y-4 overflow-y-auto px-5 py-4" aria-live="polite">
        {mensagens.length === 0 && (
          <div className="flex flex-wrap gap-2">
            {sugestoes.map((s) => (
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
          placeholder={placeholder}
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
