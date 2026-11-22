import type { Metadata } from "next";
import { Inter } from "next/font/google";
import { Suspense } from "react";

import { AppShell } from "@/components/AppShell";
import { Rodape } from "@/components/Rodape";
import { SCRIPT_TEMA } from "@/components/SeletorTema";

import "./globals.css";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter", display: "swap" });

export const metadata: Metadata = {
  title: { default: "Rastro da Emenda", template: "%s · Rastro da Emenda" },
  description: "Segue cada real da emenda parlamentar até o contrato no município — e avisa quando o rastro some.",
  icons: { icon: "/marca/qkvworks-simbolo.svg" },
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="pt-BR" className={inter.variable} data-tema="escuro" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: SCRIPT_TEMA }} />
      </head>
      <body className="font-sans antialiased">
        <AppShell
          rodape={
            <Suspense fallback={<p>Atualização: carregando…</p>}>
              <Rodape />
            </Suspense>
          }
        >
          {children}
        </AppShell>
      </body>
    </html>
  );
}
