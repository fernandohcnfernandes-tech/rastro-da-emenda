"use client";

import { Moon, Sun } from "lucide-react";
import { useSyncExternalStore } from "react";

const CHAVE = "rastro:tema";
const EVENTO = "rastro:tema";

/** Script executado no <head>, antes da pintura: aplica o tema salvo ou o do sistema (evita flash). */
export const SCRIPT_TEMA = `try{var t=localStorage.getItem("${CHAVE}");if(!t&&window.matchMedia("(prefers-color-scheme: light)").matches)t="claro";document.documentElement.dataset.tema=t||"escuro"}catch(e){}`;

function assinar(aviso: () => void) {
  window.addEventListener(EVENTO, aviso);
  window.addEventListener("storage", aviso);
  return () => {
    window.removeEventListener(EVENTO, aviso);
    window.removeEventListener("storage", aviso);
  };
}

export function SeletorTema() {
  const tema = useSyncExternalStore(
    assinar,
    () => document.documentElement.dataset.tema ?? "escuro",
    () => "escuro",
  );
  const claro = tema === "claro";
  function alternar() {
    const novo = claro ? "escuro" : "claro";
    document.documentElement.dataset.tema = novo;
    localStorage.setItem(CHAVE, novo);
    window.dispatchEvent(new Event(EVENTO));
  }
  return (
    <button
      onClick={alternar}
      className="grid h-10 w-10 shrink-0 place-items-center rounded-lg border border-borda bg-campo text-apoio transition hover:border-primaria hover:text-forte"
      aria-label={claro ? "Usar tema escuro" : "Usar tema claro"}
      title={claro ? "Tema escuro" : "Tema claro"}
    >
      {claro ? <Moon className="h-4 w-4" /> : <Sun className="h-4 w-4" />}
    </button>
  );
}
