import type { Metadata } from "next";
import Link from "next/link";
import { Suspense } from "react";

import { Rodape } from "@/components/Rodape";

import "./globals.css";

export const metadata: Metadata = {
  title: { default: "Rastro da Emenda", template: "%s · Rastro da Emenda" },
  description: "Segue cada real da emenda parlamentar até o contrato no município — e avisa quando o rastro some.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="pt-BR">
      <body className="flex min-h-screen flex-col antialiased">
        <header className="bg-[#0B0F1A] text-white">
          <nav className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 py-3">
            <Link href="/" className="flex items-baseline gap-2">
              <span className="text-lg font-bold">Rastro da Emenda</span>
              <span className="text-xs text-slate-400">por QKV works</span>
            </Link>
            <div className="flex gap-5 text-sm">
              <Link href="/" className="hover:text-blue-300">
                Início
              </Link>
              <Link href="/busca" className="hover:text-blue-300">
                Emendas
              </Link>
              <Link href="/como-funciona" className="hover:text-blue-300">
                Como funciona
              </Link>
            </div>
          </nav>
        </header>
        <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-8">{children}</main>
        <footer className="border-t border-slate-200 bg-white">
          <div className="mx-auto flex max-w-6xl flex-col gap-2 px-4 py-5 text-xs text-[#64748B] sm:flex-row sm:items-center sm:justify-between">
            <div>
              <p className="font-semibold text-[#0B0F1A]">QKV works · A próxima resposta pode transformar seu negócio.</p>
              <p>O sistema aponta indícios para apuração, nunca acusações. Fontes oficiais: Transferegov, Portal da Transparência, IBGE, PNCP e Querido Diário.</p>
            </div>
            <Suspense fallback={<p>Última atualização: carregando…</p>}>
              <Rodape />
            </Suspense>
          </div>
        </footer>
      </body>
    </html>
  );
}
