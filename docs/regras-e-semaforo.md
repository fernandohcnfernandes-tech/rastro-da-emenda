# Semáforo de execução e regras de alerta

## Semáforo (um status por plano de ação / emenda Pix)

| Status | Cor | Condição |
|---|---|---|
| `verde` | `#16A34A` | Ao menos um contrato (PNCP) ou extrato de contrato (Querido Diário) compatível com o objeto e com valor coerente, com confiança da IA ≥ 0,6 |
| `amarelo` | `#EAB308` | Evidência parcial: licitação/contratação em andamento sem contrato, contrato compatível que cobre só parte do valor, ou **execução declarada** sem documento independente: relatório de gestão entregue (final ou parcial, DISPONIBILIZADO/ENVIADO_PARA_ANALISE) declarando ≥ 70% do repassado como executado, ou **execução contábil**: o ente empenhou ≥ 70% das emendas Pix recebidas há mais de 180 dias (SICONFI, fonte 706) |
| `laranja` | `#EA580C` | **Em revisão:** há documento possivelmente compatível, com confiança da IA entre 0,45 e 0,59 — abaixo do mínimo para contar como evidência. Pede conferência humana; não é evidência nem ausência (não gera A1) |
| `vermelho` | `#DC2626` | **Indício para apuração:** pago há mais de 180 dias, nenhuma evidência nas fontes consultadas **e um sinal contrário à execução**: a contabilidade do ente (SICONFI) mostra menos de 30% das emendas Pix recebidas há mais de 180 dias empenhadas ou pré-empenhadas (A9), ou o relatório de gestão final declara menos de 70% executado (A8) |
| `azul` | `#2563EB` | **Sem evidência localizada** (neutro): nenhum documento compatível nas fontes consultadas — ou nenhuma fonte cobre o ente — e nenhum sinal contrário à execução |
| `cinza` | `#94A3B8` | Dados insuficientes (sem pagamento ainda, plano de ação incompleto, CNPJ não resolvido), pago há menos de 180 dias ou **verificação em andamento** (PNCP ainda não consultado para os CNPJs da emenda) |

**Relatório de gestão.** É declaração do próprio ente, não documento independente: nunca leva a verde. Relatório entregue (final ou parcial) com ≥ 70% executado leva a amarelo quando não há contrato nem contratação compatível (o alerta A1 continua valendo); quando há contrato, só entra na justificativa. Relatórios em elaboração não mudam o status. O A8 olha só o relatório final.

**Contabilidade do ente (SICONFI).** A Matriz de Saldos Contábeis traz a fonte de recursos 706 (transferências especiais da União): `1706` no exercício e `2706` para recursos de anos anteriores. Somamos o empenhado de 2024 (só `1706`, para não contar recursos de 2023) até a matriz mais recente e dividimos pelas emendas Pix pagas ao ente (Transferegov) até 180 dias antes da referência. O empenhado inclui o empenho inscrito em restos a pagar (contas 6.2.2.1.3.05 a .07), para onde vai na matriz de dezembro o empenho ainda não liquidado. O sinal só vale quando o ente classifica as emendas Pix nessa fonte (receita na fonte 706 ≥ 50% do recebido) e também orça por ela (dotação atualizada na fonte 1706 ≥ 50% da receita; quem recebe na 706 mas não orça nela executa por outra fonte, e empenho zero ali não diz nada), quando todas as matrizes desde 2024 foram entregues e para emendas pagas antes do corte. É declaração do ente e é agregada por ente (todas as emendas Pix juntas): ≥ 70% empenhado leva no máximo a amarelo; < 30% leva a vermelho (A9); entre os dois, só entra na justificativa. O pré-empenho (conta 6.2.2.1.2.02, crédito reservado para licitação ou contrato em curso) do ano da referência soma ao empenhado só para o A9: se empenhado < 30% mas empenhado + pré-empenhado ≥ 30%, a emenda fica `cinza` ("execução em andamento"). O bloqueio de crédito (6.2.2.1.2.01, contingenciamento) e outras indisponibilidades (.99) não contam como execução e só aparecem na justificativa.

**Por que a ausência de documento não é vermelho.** Em 23/11/2026, nas 1.817 emendas cujo relatório final declara ≥ 70% executado, a busca automática encontrou contrato ou contratação compatível em 21,9% (IC 95%: 20–24%). A proporção de emendas sem documento (≈ 79%) era praticamente igual à esperada se todas tivessem sido executadas; a ausência de documento, sozinha, não distingue emenda executada de não executada.

Ordem de decisão: `cinza` (dados) → `verde` → `amarelo` (documento parcial, execução declarada, execução contábil) → `laranja` → `cinza` (verificação em andamento; dentro do prazo; empenho em andamento pelo pré-empenho) → `vermelho` (só com A9 ou A8) → `azul`.

Prazo de referência: 180 dias contados da data do primeiro pagamento (configurável em `PRAZO_SEM_EVIDENCIA_DIAS`).

## Regras de alerta (indícios para apuração)

| Código | Regra | Dados |
|---|---|---|
| A1 | Pago sem contratação ou contrato encontrado após o prazo de referência, nas fontes que cobrem o ente | ordens de pagamento × evidências × população/cobertura |
| A2 | Plano de trabalho genérico (ex.: só "pavimentação") | texto do plano de trabalho classificado pela IA |
| A3 | Relatório de gestão ausente ou pendente | `relatorio_gestao_*` |
| A4 | Menos de 70% em despesas de capital (art. 166-A da Constituição) | `valor_investimento / (valor_custeio + valor_investimento)` |
| A5 | Objeto do contrato diferente do objeto da emenda | comparação pela IA com justificativa |
| A6 | Contratação direta (dispensa ou inexigibilidade) com o recurso | modalidade no PNCP / tipo de ato no diário |
| A7 | Valor contratado muito acima ou abaixo do repassado | razão contrato/repasse fora de [0,5; 1,5] (configurável) |
| A8 | Relatório de gestão final declara menos de 70% do repassado como executado | `relatorio_gestao` (formato novo: tipo, situação, valor executado) × pagamentos |
| A9 | Contabilidade do ente mostra menos de 30% das emendas Pix recebidas há mais de 180 dias empenhadas ou pré-empenhadas | MSC do SICONFI (fonte 706) × pagamentos do Transferegov |
| A10 (extensão) | Fornecedor sancionado (CEIS/CNEP) ou com CNPJ aberto há menos de 6 meses | cadastros de sanções e data de abertura |

## Pré-filtro antes da IA

Para cada emenda, candidatos = evidências do(s) CNPJ(s) beneficiário/executor com:
- data de publicação ≥ data do primeiro pagamento − 30 dias;
- valor entre 10% e 200% do valor repassado (ou sem valor informado);
- similaridade de texto (TF-IDF ou embeddings) entre objeto da evidência e objeto/plano de trabalho ≥ limiar;
- no máximo os 5 melhores candidatos por emenda seguem para a IA.

## Contrato da resposta da IA

```json
{
  "compativel": true,
  "confianca": 0.82,
  "tipo_ato": "extrato_contrato",
  "objeto_extraido": "pavimentação em paralelepípedo da Rua X",
  "valor_extraido": 350000.00,
  "fornecedor_cnpj": "12345678000190",
  "justificativa": "O objeto do contrato coincide com a meta 1 do plano de trabalho...",
  "trechos_citados": ["...trecho literal da fonte..."]
}
```

Linguagem obrigatória na interface e no dossiê: "indício", "sem evidência encontrada nas fontes consultadas". Nunca "irregular", "desvio" ou "fraude".
