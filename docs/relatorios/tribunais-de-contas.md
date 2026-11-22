# Tribunais de Contas: dados abertos de contratos municipais

Levantamento de 22/11/2026, feito para cobrir municípios com até 20 mil habitantes que não publicam no PNCP. "Testado" = chamada real a partir do servidor do projeto; "lido" = só documentação. Só fontes oficiais; nada de captcha, login, raspagem de HTML ou contorno de bloqueio.

**Atenção:** o servidor de desenvolvimento sai pela internet com IP dos EUA. Vários TCEs não aceitam conexão a partir dele (MG, AL, AC, AP, RR, MS, MT, TCM-BA). Isso parece bloqueio geográfico ou de datacenter e precisa ser reavaliado a partir de um IP brasileiro, sem nenhuma tentativa de contorno.

| UF | Órgão | Fonte | Contratos municipais? | Teste | Veredito |
|---|---|---|---|---|---|
| **RS** | TCE-RS | `dados.tce.rs.gov.br/dados/licitacon/contrato/ano/{ano}.csv.zip` + cadastro de órgãos com CNPJ/IBGE | sim | 200; 170.643 contratos relevantes carregados | **INTEGRADO** |
| SP | TCE-SP (Audesp) | `transparencia.tce.sp.gov.br/.../licitacoes-contratos/ajustes-{ano}-{semestre}.zip` (CSV) | sim (644 municípios; capital é do TCM-SP) | 200; 17,8 MB zip / 250 MB csv; CNPJ da contratada e empenho; entidade só por nome | USAR (próxima) |
| PI | TCE-PI (muralcon) | `sistemas.tce.pi.gov.br/muralcon/api/contratos?esfera=municipal&expand=true&vigencia=AAAA-MM-DD_AAAA-MM-DD` | sim | 200; ~30 mil contratos municipais em 2025; filtro por `codibge`; CNPJ da contratada | USAR (mais simples) |
| RN | TCE-RN | `apidadosabertos.tce.rn.gov.br/api/ContratosApi/Contratos/Json/{unidade}/true` + `/api/InformacoesBasicasApi/JurisdicionadosTCE/json` (923 unidades com CNPJ) | sim | 200; objeto, valor, assinatura, contratado, PDF | USAR |
| CE | TCE-CE (SIM) | `api-dados-abertos.tce.ce.gov.br/sim/contratos?codigo_municipio=002&data_inicio=20240101&data_fim=20241231` (datas AAAAMMDD) | sim | 200; fornecedor em `/contratados`; texto com dupla codificação UTF-8 | USAR |
| RJ | TCE-RJ | `dados.tcerj.tc.br/api/v1/contratos_municipio?ano=2025` | sim (exceto a capital) | 200; tem `PossuiRecursoDaUniao`; parte dos CNPJ mascarados | USAR |
| ES | TCE-ES (dados.es.gov.br, "tcees-contratacoes") | CSV bianual `instrumentos.csv` | sim | 200; contratante por nome da UG | USAR |
| PE | TCE-PE | `sistemas.tce.pe.gov.br/DadosAbertos/Contratos!json?AnoContrato=&Municipio=` | sim | 200; objeto às vezes pobre; limite de 10 mil por consulta | TALVEZ |
| PB | TCE-PB | `download.tce.pb.gov.br/dados-abertos/dados-consolidados/licitacoes/licitacoes-{ano}.zip` | só licitações (com vencedor) | 200; 4,5 MB zip | TALVEZ (serve para amarelo) |
| PR | TCE-PR | `servicos.tce.pr.gov.br/.../muraldelicitacoes/*.csv` | só licitações e obras | 200 | TALVEZ (amarelo) |
| MA | TCE-MA | `tce-api.apps.tcema.tc.br/sacop/contrato` (swagger) | sim pela documentação | 400 (backend fora do ar no teste) | TALVEZ |
| MG | TCE-MG | dadosabertos.tce.mg.gov.br | sim, segundo o TCE | sem conexão daqui (provável bloqueio geográfico) | reavaliar com IP brasileiro |
| BA | TCM-BA | tcm.ba.gov.br/dados-abertos | desconhecido | sem conexão daqui | reavaliar com IP brasileiro |
| MT | TCE-MT | radar.tce.mt.gov.br (indício de API) | desconhecido | sem conexão daqui | reavaliar com IP brasileiro |
| GO | TCM-GO | `acessoainformacao.tcmgo.tc.br/api/contratos_tcm` | só do próprio TCM | 200 | NÃO |
| SC | TCE-SC | `servicos.tcesc.tc.br/endpoints-portal-transparencia/` | não (só cadastros; e-Sfinge fechado) | 200 | NÃO |
| SE | TCE-SE | `/visualizadorRelatorios/api/Contratos/ContratosVigentes` | só do próprio TCE | 200 | NÃO |
| AM | TCE-AM | eContas (JSF) | só em tela HTML | 302 | NÃO |
| PA | TCM-PA | mural de licitações | só em tela | 403 anti-bot | NÃO |
| RO | TCE-RO | APIs do próprio TCE; SIGAP em HTML | não | 403 | NÃO |
| TO | TCE-TO | dados abertos do e-Contas | não (processos e decisões) | lido | NÃO |
| AC, AL, AP, RR, MS | — | — | não encontrado | sem conexão / só dados do próprio tribunal | NÃO |

Ordem sugerida para as próximas integrações: **PI** (API com filtro por IBGE), **SP** (maior cobertura), **RN**, depois CE, RJ e ES. Licitações de PB e PR podem alimentar o amarelo.
