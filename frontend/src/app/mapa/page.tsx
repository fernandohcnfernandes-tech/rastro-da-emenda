import { MapaBrasil } from "@/components/MapaBrasil";
import { CabecalhoPagina, Cartao } from "@/components/ui";

export const metadata = { title: "Mapa" };

export default function PaginaMapa() {
  return (
    <>
      <CabecalhoPagina
        rotulo="Explorar"
        titulo="Mapa do semáforo"
        descricao="Cada município recebe a cor das emendas Pix que recebeu: vermelho se houver ao menos uma com indício; senão, a cor da maioria. Clique para ver o resumo."
      />
      <Cartao>
        <MapaBrasil painel />
      </Cartao>
    </>
  );
}
