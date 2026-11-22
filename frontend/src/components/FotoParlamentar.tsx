/* eslint-disable @next/next/no-img-element */
import { UserRound } from "lucide-react";

/** Foto oficial (Câmara/Senado) ou um marcador neutro quando não houver. */
export function FotoParlamentar({ url, nome, tamanho = 40 }: { url: string | null; nome: string; tamanho?: number }) {
  if (!url)
    return (
      <span className="grid shrink-0 place-items-center rounded-full bg-superficie-3 text-discreto" style={{ width: tamanho, height: tamanho }}>
        <UserRound className="h-1/2 w-1/2" />
      </span>
    );
  return (
    <img
      src={url}
      alt={`Foto oficial de ${nome}`}
      loading="lazy"
      referrerPolicy="no-referrer"
      className="shrink-0 rounded-full border border-borda object-cover object-top"
      style={{ width: tamanho, height: tamanho }}
    />
  );
}
