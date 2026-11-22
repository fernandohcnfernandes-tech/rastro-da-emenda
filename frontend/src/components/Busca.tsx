export function Busca({ valor = "", grande = false }: { valor?: string; grande?: boolean }) {
  return (
    <form action="/busca" method="get" role="search" className="flex w-full gap-2">
      <input
        name="q"
        defaultValue={valor}
        aria-label="Buscar"
        placeholder="Município, parlamentar, número da emenda ou objeto (ex.: ambulância)"
        className={`min-w-0 flex-1 rounded-md border border-slate-300 bg-white px-4 text-[#0B0F1A] shadow-sm focus:border-[#2563EB] focus:outline-none ${grande ? "py-3 text-base" : "py-2 text-sm"}`}
      />
      <button className={`rounded-md bg-[#2563EB] px-5 font-semibold text-white hover:bg-blue-700 ${grande ? "py-3" : "py-2 text-sm"}`}>
        Buscar
      </button>
    </form>
  );
}
