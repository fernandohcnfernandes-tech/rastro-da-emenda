import { redirect } from "next/navigation";
import { Suspense } from "react";

type Params = Record<string, string | string[] | undefined>;

async function Redirecionar({ searchParams }: { searchParams: Promise<Params> }) {
  const sp = await searchParams;
  const q = Array.isArray(sp.q) ? sp.q[0] : sp.q;
  redirect(q ? `/emendas?q=${encodeURIComponent(q)}` : "/emendas");
  return null;
}

/** Endereço antigo da busca: redireciona para /emendas. */
export default function Busca({ searchParams }: { searchParams: Promise<Params> }) {
  return (
    <Suspense>
      <Redirecionar searchParams={searchParams} />
    </Suspense>
  );
}
