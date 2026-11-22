# Submissão — Hack Brasil 2026

## Nome
Rastro da Emenda

## Frase de apresentação
Segue cada real da emenda parlamentar até o contrato no município — e avisa quando o rastro some.

## Trilha
Logística & automação (integração entre sistemas e automação de fluxo de informação).

## Descrição (até 1.500 caracteres)

<!-- DESCRICAO -->
As emendas Pix (transferências especiais) somam bilhões por ano e caem direto no caixa de estados e municípios, sem convênio e sem conta específica. Saber se o dinheiro virou obra ou serviço exige cruzar à mão sistemas que não conversam. O Rastro da Emenda automatiza esse fluxo: integra Transferegov, Portal da Transparência e IBGE (quem indicou, quanto, para quem, quando foi pago e o que foi prometido) com o PNCP e, nos municípios de até 20 mil habitantes, com os diários oficiais do Querido Diário (o que foi licitado e contratado). Um motor filtra candidatos por CNPJ do beneficiário e dos executores, data, valor e semelhança de texto, e uma IA com saída estruturada decide se o contrato corresponde ao objeto da emenda, sempre citando o trecho e o link oficial. Cada emenda recebe um semáforo (verde, amarelo, vermelho, azul ou cinza), alertas como pagamento sem contrato após 180 dias, plano genérico, contratação direta e valor desproporcional, além de um dossiê em PDF. Mapa por município, páginas por parlamentar e alertas por e-mail completam a ferramenta, com atualização semanal automática. Cobre todas as emendas Pix desde 2024. O sistema aponta indícios para apuração, nunca acusações, e diferencia "sem evidência" de "sem fonte para verificar". Só usa APIs oficiais e mascara dados pessoais.
<!-- /DESCRICAO -->

## Links
- Repositório: https://github.com/fernandohcnfernandes-tech/rastro-da-emenda
- Demo: https://rastrodaemenda.com.br
- Vídeo (até 3 min, sem login, em português): _preencher com o link_

## Roteiro do vídeo (3 minutos)

| Tempo | Cena | Fala (resumo) |
|---|---|---|
| 0:00–0:20 | Manchetes sobre emendas Pix; tela inicial | "Em 2024 e 2025, bilhões em emendas Pix caíram direto no caixa das prefeituras. Para onde foi esse dinheiro?" |
| 0:20–0:45 | Diagrama das fontes (README) | "O Rastro da Emenda liga Transferegov, Portal da Transparência, IBGE, PNCP e diários oficiais — sistemas que não conversam." |
| 0:45–1:15 | Mapa do Brasil colorido; troca de UF; passa o mouse num município | "Cada município ganha a cor do semáforo das emendas que recebeu. Vermelho é indício para apuração; azul é quando não há fonte pública para verificar." |
| 1:15–1:55 | Busca por um município → ficha de emenda verde: linha do tempo até o contrato, link do PNCP | "Aqui a emenda foi paga em março e o contrato compatível aparece no PNCP em julho, com objeto e valor coerentes. Um clique e você está no documento oficial." |
| 1:55–2:25 | Ficha vermelha: alertas A1/A3; botão do dossiê; PDF aberto | "Aqui: pago há mais de 180 dias, nenhum contrato nas fontes que cobrem o município e relatório de gestão pendente. O dossiê em PDF reúne tudo para quem vai apurar." |
| 2:25–2:45 | Página do parlamentar; formulário de alerta por e-mail | "Jornalistas, conselhos e cidadãos podem acompanhar um parlamentar ou município e receber e-mail quando o status muda. Tudo é atualizado toda semana, automaticamente." |
| 2:45–3:00 | Página Como funciona; logo QKV works | "Só APIs oficiais, dados pessoais mascarados, código aberto. Rastro da Emenda — equipe QKV. A próxima resposta pode transformar seu negócio." |

Dicas de gravação: tela em 1920×1080, zoom do navegador em 110%, escolher previamente uma emenda verde, uma vermelha e uma azul reais (ver `docs/conferencia-amostra.md`).

## Checklist do regulamento
- [x] Repositório público, licença MIT, todo o código escrito no evento
- [x] Nenhum segredo no histórico (varredura em 22/11/2026)
- [x] Demo no ar: https://rastrodaemenda.com.br (brasil4; manter no ar durante a avaliação)
- [ ] Vídeo gravado e link preenchido
- [ ] Aceite do regulamento no formulário
- [ ] Último commit até 30/11/2026, 23h59 (horário de Brasília) — depois disso, congelamento
