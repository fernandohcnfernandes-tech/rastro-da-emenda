import { CabecalhoPagina } from "@/components/ui";
import { CORES, ROTULOS } from "@/lib/formato";
import type { Status } from "@/lib/tipos";

export const metadata = { title: "Como funciona" };

const SEMAFORO: [Status, string][] = [
  ["verde", "Há contrato (PNCP) ou extrato de contrato (diário oficial) compatível com o objeto e o valor da emenda, com confiança de pelo menos 60%."],
  ["amarelo", "Evidência parcial: licitação ou contratação em andamento sem contrato, ou contratos compatíveis que cobrem menos de 70% do valor repassado."],
  ["vermelho", "Pago há mais de 180 dias e nenhuma evidência nas fontes que cobrem o ente. É um indício para apuração, nunca uma acusação."],
  ["azul", "Município com até 20 mil habitantes, sem registros no PNCP, fora da cobertura do Querido Diário e sem dados abertos de contratos do Tribunal de Contas: não há fonte pública para verificar. Neutro."],
  ["cinza", "Dados insuficientes (sem pagamento, sem objeto ou sem código IBGE) ou pagamento recente, ainda dentro do prazo de 180 dias."],
];

const ALERTAS: [string, string][] = [
  ["A1", "Pago sem contratação ou contrato encontrado após o prazo de referência, nas fontes que cobrem o ente."],
  ["A2", "Plano de trabalho genérico (ex.: só “pavimentação” ou lista de áreas), que impede verificar a execução."],
  ["A3", "Relatório de gestão ausente ou pendente depois do prazo."],
  ["A4", "Menos de 70% do valor em despesas de capital (art. 166-A da Constituição)."],
  ["A5", "Há contrato do ente no período e na faixa de valor, mas com objeto diferente do da emenda."],
  ["A6", "Contratação direta (dispensa ou inexigibilidade) associada ao recurso."],
  ["A7", "Valor contratado muito acima ou abaixo do repassado (fora de 50% a 150%)."],
];

const FONTES: [string, string, string][] = [
  ["Transferegov — Transferências Especiais (MGI)", "Planos de ação, executores, metas, empenhos, ordens bancárias e relatórios de gestão.", "https://api.transferegov.gestao.gov.br/transferenciasespeciais/"],
  ["Portal da Transparência (CGU)", "Emendas parlamentares, autor e objeto declarado de cada plano de ação.", "https://portaldatransparencia.gov.br/emendas"],
  ["IBGE", "Códigos de municípios, população estimada e malha do mapa.", "https://servicodados.ibge.gov.br/api/docs"],
  ["PNCP — Portal Nacional de Contratações Públicas", "Contratos e contratações dos CNPJs beneficiários e executores.", "https://pncp.gov.br/api/consulta/swagger-ui/index.html"],
  ["Querido Diário (Open Knowledge Brasil)", "Diários oficiais de municípios pequenos cobertos pelo projeto.", "https://queridodiario.ok.org.br"],
  ["Tribunais de Contas — dados abertos", "Contratos que os municípios informam ao TCE-RS (LicitaCon), TCE-SP (Audesp), TCE-PI (Mural de Contratos) e TCE-RN.", "https://dados.tce.rs.gov.br"],
];

export default function ComoFunciona() {
  return (
    <article className="max-w-4xl space-y-8 leading-relaxed text-cinza-claro">
      <CabecalhoPagina rotulo="Sobre" titulo="Como funciona" />
      <header>
        <p className="text-apoio">
          O Rastro da Emenda acompanha as <strong>transferências especiais (“emendas Pix”)</strong> destinadas a estados e municípios de 2024
          até hoje. Para cada plano de ação, coletamos os dados federais, procuramos evidências de uso do dinheiro no ente beneficiário e
          classificamos a execução num semáforo. Os dados são atualizados toda semana.
        </p>
      </header>

      <section className="rounded-xl border border-vermelho/40 bg-vermelho/10 p-4 text-sm text-vermelho-claro">
        <strong>Aviso importante:</strong> o sistema aponta <strong>indícios para apuração</strong>, nunca acusações. “Sem evidência encontrada
        nas fontes consultadas” significa apenas que nada foi localizado nas bases públicas — o recurso pode ter sido aplicado e publicado em
        outro lugar. Toda conclusão traz o link para o documento oficial que a sustenta.
      </section>

      <section>
        <h2 className="mb-2 text-lg font-semibold text-texto">O caminho do dinheiro</h2>
        <ol className="mt-2 list-decimal space-y-1 pl-5 text-cinza-claro">
          <li>Coletamos valor, parlamentar, beneficiário, executores, pagamentos e plano de trabalho (Transferegov e Portal da Transparência).</li>
          <li>Procuramos contratos e contratações do CNPJ beneficiário e dos executores no PNCP, a partir do 1º pagamento (menos 30 dias).</li>
          <li>Em municípios com até 20 mil habitantes, também buscamos extratos de contrato, avisos de licitação e dispensas no Querido Diário.</li>
          <li>Em RS, SP, PI e RN, usamos também os contratos que os municípios informam ao Tribunal de Contas do estado, em dados abertos.</li>
          <li>Um pré-filtro (CNPJ, data, faixa de valor e semelhança de texto) seleciona até 5 candidatos por emenda.</li>
          <li>Uma IA compara cada candidato com o objeto da emenda e devolve compatibilidade, confiança, justificativa e trechos citados. Sem IA configurada, uma regra transparente de semelhança e valor faz essa etapa — e a ficha indica isso.</li>
          <li>Regras de alerta e o semáforo são calculados e geram a ficha, o dossiê em PDF e os alertas por e-mail.</li>
        </ol>
      </section>

      <section>
        <h2 className="mb-2 text-lg font-semibold text-texto">Semáforo</h2>
        <ul className="mt-3 space-y-3">
          {SEMAFORO.map(([s, d]) => (
            <li key={s} className="flex gap-3">
              <span className="mt-1 h-4 w-4 shrink-0 rounded-full" style={{ backgroundColor: CORES[s] }} />
              <span>
                <strong>{ROTULOS[s]}</strong> ({s}) — {d}
              </span>
            </li>
          ))}
        </ul>
      </section>

      <section>
        <h2 className="mb-2 text-lg font-semibold text-texto">Alertas (indícios)</h2>
        <ul className="mt-2 space-y-1 text-cinza-claro">
          {ALERTAS.map(([c, d]) => (
            <li key={c}>
              <strong>{c}</strong> — {d}
            </li>
          ))}
        </ul>
      </section>

      <section>
        <h2 className="mb-2 text-lg font-semibold text-texto">Fontes de dados</h2>
        <p className="text-sm text-apoio">Somente APIs e bases oficiais e abertas, respeitando os limites de requisição de cada uma.</p>
        <ul className="mt-2 space-y-2">
          {FONTES.map(([nome, uso, url]) => (
            <li key={nome}>
              <a href={url} target="_blank" rel="noreferrer" className="font-semibold text-destaque hover:underline">
                {nome}
              </a>
              <span className="text-apoio"> — {uso}</span>
            </li>
          ))}
        </ul>
      </section>

      <section>
        <h2 className="mb-2 text-lg font-semibold text-texto">Limitações</h2>
        <ul className="mt-2 list-disc space-y-1 pl-5 text-cinza-claro">
          <li>
            <strong>Municípios até 20 mil habitantes</strong> podem publicar contratações apenas no diário oficial até abril de 2027, sem
            obrigação de usar o PNCP. Neles a verificação depende do Querido Diário.
          </li>
          <li>
            <strong>Cobertura do Querido Diário e dos Tribunais de Contas:</strong> o Querido Diário tem busca de texto em cerca de 500
            municípios, e integramos os Tribunais de Contas que publicam contratos municipais em dados abertos (RS, SP, PI e RN). Município pequeno sem nenhuma dessas
            fontes e sem registros no PNCP recebe azul (sem fonte para verificar), não vermelho.
          </li>
          <li>O recurso da emenda Pix entra no caixa do ente e não exige conta específica: a ligação com um contrato é feita por objeto, valor, data e CNPJ — por isso falamos em evidência e indício.</li>
          <li>Contratos abaixo de 10% do repasse não são considerados; emendas executadas por meio de vários contratos pequenos podem aparecer como amarelo.</li>
          <li>Dados pessoais: CPF de fornecedor pessoa física aparece mascarado e o nome é omitido.</li>
        </ul>
      </section>

      <p className="text-sm text-discreto">Projeto da equipe QKV para o Hack Brasil 2026 — trilha Logística & automação. Código aberto (licença MIT).</p>
    </article>
  );
}
