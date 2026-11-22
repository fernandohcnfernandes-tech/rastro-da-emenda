# Semáforo de execução e regras de alerta

## Semáforo (um status por plano de ação / emenda Pix)

| Status | Cor | Condição |
|---|---|---|
| `verde` | `#16A34A` | Ao menos um contrato (PNCP) ou extrato de contrato (Querido Diário) compatível com o objeto e com valor coerente, com confiança da IA ≥ 0,6 |
| `amarelo` | `#EAB308` | Evidência parcial: licitação/contratação em andamento sem contrato, ou contrato compatível que cobre só parte do valor |
| `vermelho` | `#DC2626` | Pago há mais de 180 dias e nenhuma evidência nas fontes que cobrem o ente (PNCP; Querido Diário para entes cobertos; Tribunal de Contas onde há dados abertos) |
| `azul` | `#2563EB` | Município ≤ 20 mil habitantes, sem registro no PNCP e fora da cobertura do Querido Diário — **sem fonte para verificar** (neutro) |
| `cinza` | `#94A3B8` | Dados insuficientes (sem pagamento ainda, plano de ação incompleto, CNPJ não resolvido), pago há menos de 180 dias, candidato "em revisão" (confiança 0,45–0,59) ou **verificação em andamento** (PNCP ainda não consultado para os CNPJs da emenda) |

Ordem de decisão: `cinza` → `verde` → `amarelo` → (`vermelho` ou `azul`, conforme cobertura de fontes) → caso contrário `cinza`.

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
| A8 (extensão) | Fornecedor sancionado (CEIS/CNEP) ou com CNPJ aberto há menos de 6 meses | cadastros de sanções e data de abertura |

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
