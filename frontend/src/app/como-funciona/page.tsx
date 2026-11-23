import { CabecalhoPagina } from "@/components/ui";
import { CORES, ROTULOS } from "@/lib/formato";
import type { Status } from "@/lib/tipos";

export const metadata = { title: "Como funciona" };

const SEMAFORO: [Status, string][] = [
  ["verde", "Há contrato compatível com o objeto e o valor da emenda (no PNCP, no Tribunal de Contas ou em extrato publicado no diário oficial), com confiança de pelo menos 60% e cobrindo ao menos 70% do valor repassado."],
  ["amarelo", "Evidência parcial: licitação ou contratação em andamento sem contrato, contratos compatíveis que cobrem menos de 70% do valor repassado, ou execução declarada pelo próprio ente no relatório de gestão final (70% ou mais do repassado) sem documento independente localizado."],
  ["laranja", "Em revisão: há documento possivelmente compatível com a emenda, mas com confiança entre 45% e 59%, abaixo do mínimo para contar como evidência. Pede conferência humana; não é evidência de execução nem indício de problema."],
  ["vermelho", "Pago há mais de 180 dias e nenhuma evidência nas fontes que cobrem o ente. É um indício para apuração, nunca uma acusação."],
  ["azul", "Ente sem nenhuma fonte pública para verificar: município com até 20 mil habitantes sem registros no PNCP, fora da cobertura do Querido Diário e sem dados abertos de contratos do Tribunal de Contas. Neutro — não é indício de problema."],
  ["cinza", "Dados insuficientes (sem pagamento, sem objeto ou sem código IBGE); pagamento recente, ainda dentro do prazo de 180 dias; ou verificação em andamento (o ente ainda não foi consultado no PNCP)."],
];

const ALERTAS: [string, string][] = [
  ["A1", "Pago sem contratação ou contrato encontrado após o prazo de referência, nas fontes que cobrem o ente."],
  ["A2", "Plano de trabalho genérico (ex.: só “pavimentação” ou lista de áreas), que impede verificar a execução."],
  ["A3", "Relatório de gestão ausente ou pendente depois do prazo."],
  ["A4", "Menos de 70% do valor em despesas de capital (art. 166-A da Constituição)."],
  ["A5", "Há contrato do ente no período e na faixa de valor, mas com objeto diferente do da emenda."],
  ["A6", "Contratação direta (dispensa ou inexigibilidade) associada ao recurso."],
  ["A7", "Valor contratado muito acima ou abaixo do repassado (fora de 50% a 150%)."],
  ["A8", "Relatório de gestão final declara menos de 70% do valor repassado como executado."],
];

const FONTES: [string, string, string][] = [
  ["Transferegov — Transferências Especiais (MGI)", "Planos de ação, executores, metas, empenhos, ordens bancárias e relatórios de gestão.", "https://api.transferegov.gestao.gov.br/transferenciasespeciais/"],
  ["Portal da Transparência (CGU)", "Emendas parlamentares, autor e objeto declarado de cada plano de ação.", "https://portaldatransparencia.gov.br/emendas"],
  ["IBGE", "Códigos de municípios e estados, população estimada e malhas do mapa.", "https://servicodados.ibge.gov.br/api/docs"],
  ["PNCP — Portal Nacional de Contratações Públicas", "Contratos e contratações dos CNPJs beneficiários (municípios, estados e DF) e dos executores (secretarias e fundos).", "https://pncp.gov.br/api/consulta/swagger-ui/index.html"],
  ["Câmara dos Deputados e Senado Federal", "Partido, UF, foto e contato institucional dos parlamentares autores.", "https://dadosabertos.camara.leg.br"],
  ["Querido Diário (Open Knowledge Brasil)", "Extratos de contrato, avisos de licitação, homologações e dispensas nos diários oficiais.", "https://queridodiario.ok.org.br"],
  ["Tribunais de Contas (RS, SP, PI e RN)", "Contratos que municípios e órgãos estaduais informam ao tribunal, em dados abertos.", "https://dados.tce.rs.gov.br"],
];

export default function ComoFunciona() {
  return (
    <article className="max-w-4xl space-y-8 leading-relaxed text-cinza-claro">
      <CabecalhoPagina rotulo="Sobre" titulo="Como funciona" />
      <header>
        <p className="text-apoio">
          O Rastro da Emenda acompanha as <strong>transferências especiais (“emendas Pix”)</strong> destinadas a estados e municípios de 2024
          até hoje. Para cada plano de ação, coletamos os dados federais, procuramos evidências de uso do dinheiro no ente beneficiário e
          classificamos a execução num semáforo. Cobre municípios, estados e o Distrito Federal, e os dados são atualizados toda semana.
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
          <li>Para qualquer ente coberto pelo Querido Diário sem evidência no PNCP (inclusive o DF, pelo DODF), buscamos extratos de contrato, avisos de licitação, homologações e dispensas nos diários oficiais.</li>
          <li>Em RS, SP, PI e RN, usamos também os contratos que municípios e órgãos estaduais informam ao Tribunal de Contas, em dados abertos.</li>
          <li>Lemos o relatório de gestão que o próprio ente entrega no Transferegov. Por ser uma declaração do ente, e não um documento independente, o relatório final que declara 70% ou mais executado leva no máximo a amarelo (“execução declarada”), nunca a verde; o que declara menos de 70% gera o alerta A8. Relatórios parciais ou em elaboração não mudam o status.</li>
          <li>Um pré-filtro (CNPJ, data, faixa de valor e semelhança de texto) seleciona até 5 candidatos por emenda. Documento que cita o número da emenda entra sempre, na frente.</li>
          <li>A IA (Claude Haiku 5.5, da Anthropic) compara cada candidato com o objeto e o valor da emenda e devolve compatibilidade, confiança, justificativa e trechos citados. Se a IA estiver indisponível, uma regra transparente de semelhança e valor faz essa etapa, e a ficha indica que a classificação foi heurística.</li>
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

        <div className="mt-6 space-y-3">
          <h3 className="font-semibold text-texto">Querido Diário</h3>
          <p>
            O{" "}
            <a href="https://queridodiario.ok.org.br" target="_blank" rel="noreferrer" className="font-semibold text-destaque hover:underline">
              Querido Diário
            </a>{" "}
            é uma iniciativa de tecnologia cívica da <strong>Open Knowledge Brasil</strong>, organização sem fins lucrativos que promove dados abertos
            e transparência. O projeto coleta os diários oficiais publicados pelas prefeituras — cada uma num site e formato diferente, muitas vezes em
            PDF —, extrai o texto e o disponibiliza de forma padronizada, com busca e uma API pública e gratuita. O código é aberto e feito com a
            participação de voluntários. Para municípios que não publicam suas contratações no PNCP (em especial os com até 20 mil habitantes, que
            podem usar só o diário oficial até 2027), é a principal forma de encontrar extratos de contrato e avisos de licitação. A cobertura com
            texto pesquisável alcança cerca de 500 municípios e cresce continuamente; no DF, inclui o Diário Oficial do Distrito Federal (DODF).
          </p>
          <h3 className="pt-2 font-semibold text-texto">Tribunais de Contas</h3>
          <p>
            Todos os municípios e estados prestam contas de licitações e contratos aos Tribunais de Contas, mas cada tribunal publica esses dados
            de um jeito. Usamos <strong>apenas os que disponibilizam os dados por API pública ou arquivo aberto, sem cadastro, captcha ou login</strong>:
            hoje, o{" "}
            <a href="https://dados.tce.rs.gov.br" target="_blank" rel="noreferrer" className="text-destaque hover:underline">TCE-RS</a> (LicitaCon), o{" "}
            <a href="https://transparencia.tce.sp.gov.br" target="_blank" rel="noreferrer" className="text-destaque hover:underline">TCE-SP</a> (Audesp), o{" "}
            <a href="https://www.tcepi.tc.br/portaldacidadania/dados-abertos" target="_blank" rel="noreferrer" className="text-destaque hover:underline">TCE-PI</a>{" "}
            (Mural de Contratos) e o{" "}
            <a href="https://apidadosabertos.tce.rn.gov.br" target="_blank" rel="noreferrer" className="text-destaque hover:underline">TCE-RN</a>. Nos demais
            estados, os dados de contratos municipais não estão disponíveis em formato aberto ou só aparecem em páginas de consulta, que não usamos
            para respeitar os termos de uso dos sites.
          </p>
        </div>
      </section>

      <section>
        <h2 className="mb-2 text-lg font-semibold text-texto">Inteligência artificial</h2>
        <ul className="mt-2 list-disc space-y-1 pl-5 text-cinza-claro">
          <li>
            <strong>Classificação dos documentos:</strong> o Claude Haiku 5.5 decide se cada contrato, licitação ou extrato corresponde ao objeto e
            ao valor da emenda. Só confiança de 60% ou mais conta como evidência; entre 45% e 59%, a emenda fica em revisão.
          </li>
          <li>
            <strong>Assistente de análise</strong> (aba “Assistente IA” na ficha da emenda): o Claude Sonnet 5.5 responde perguntas sobre a emenda e
            os documentos, consultando apenas o banco do projeto — documentos do ente, outras emendas do beneficiário e detalhes de cada documento. Ele
            fala em indícios, nunca em acusação, e cita a fonte de cada afirmação com o link oficial.
          </li>
          <li>
            <strong>Pergunte à IA</strong> (menu Análise): o mesmo assistente responde perguntas gerais sobre os dados do portal — rankings por
            UF, município, parlamentar ou partido, situação de um município, emendas por tema — e cita as fichas usadas.
          </li>
          <li>
            <strong>Dossiê com análise da IA:</strong> versão do PDF que acrescenta um parecer gerado pelo assistente, identificado como tal.
          </li>
          <li>A IA pode errar: confira sempre o documento oficial antes de tirar conclusões. Nenhum CPF é enviado à IA.</li>
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
            municípios (e no DF), e só integramos os Tribunais de Contas com API pública ou dados abertos (RS, SP, PI e RN). Município pequeno
            sem nenhuma dessas fontes e sem registros no PNCP recebe azul (sem fonte para verificar), não vermelho.
          </li>
          <li>
            <strong>Estados e DF:</strong> buscamos contratos do CNPJ do governo e dos órgãos executores indicados no plano de ação. Contratos
            assinados por outros órgãos estaduais só entram quando o Tribunal de Contas publica os dados (RS, PI e RN).
          </li>
          <li>O recurso da emenda Pix entra no caixa do ente e não exige conta específica: a ligação com um contrato é feita por objeto, valor, data e CNPJ — por isso falamos em evidência e indício.</li>
          <li>Contratos abaixo de 10% do repasse não são considerados; emendas executadas por meio de vários contratos pequenos podem aparecer como amarelo.</li>
          <li>A verificação no PNCP é feita ente a ente, no limite de requisições do portal; enquanto um ente não é consultado, suas emendas ficam cinza (“verificação em andamento”).</li>
          <li>Dados pessoais: CPF de fornecedor pessoa física aparece mascarado e o nome é omitido.</li>
        </ul>
      </section>

      <p className="text-sm text-discreto">Projeto da equipe QKV para o Hack Brasil 2026 — trilha Logística & automação. Código aberto (licença MIT).</p>
    </article>
  );
}
