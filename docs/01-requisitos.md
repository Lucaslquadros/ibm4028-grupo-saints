# Documento de Requisitos

**IBM4028 — Projeto em Ciência de Dados IV | IBMEC CDIA | 2026.2**

| | |
|---|---|
| **Grupo** | _(nomes)_ |
| **Cliente (papel de PO)** | Sócio do Grupo Saints (grupo de bares/restaurantes, [gruposaints.com.br](https://www.gruposaints.com.br/)) — contato via entrevista, nome não identificado na transcrição |
| **Versão** | 0.2 — rascunho, baseado na Conversa 1 |
| **Última atualização** | 13/09/2026 |

> Este documento é a base da **AC2 (entrega de 21/09/2026)** e da **Entrega Parcial 1**, e é atualizado a cada sprint.
> Requisito que mudar aparece aqui **com o motivo** — mudança silenciosa é escopo fora de controle.
>
> Ao preencher, use a skill `requisitos-ibm4028` (está em `.claude/skills/`).

---

## 1. Visão Geral

### 1.1 Problema

> Formato: **"[Persona] precisa de [necessidade] porque [insight]."**
> Se não menciona quem sofre, qual a dor e qual o impacto, ainda não está definido.

_(uma frase)_

### 1.2 Como o problema é resolvido hoje

_(planilha? WhatsApp? caderno? outro sistema? A gambiarra atual é a melhor evidência de que a dor é real.)_

### 1.3 Impacto medido

| Dimensão | Situação atual | Meta com a solução |
|---|---|---|
| Tempo gasto | _(ex: 4h por semana)_ | |
| Custo | | |
| Frequência do problema | | |
| Erros / retrabalho | | |

### 1.4 Objetivo do projeto

_(o que o sistema entrega, em uma frase)_

### 1.5 Escopo

**Dentro:**

**Fora (explicitamente):**

### 1.6 Como o sucesso será medido

_(a métrica que comprova que o problema foi resolvido)_

---

## 2. Stakeholders

| Stakeholder | Papel | Interesse | Influência |
|---|---|---|---|
| _(nome)_ | Cliente / PO | Valida entregas, prioriza | Alta |
| Professor | Sponsor | Avalia a disciplina | Alta |
| _(grupo)_ | Dev Team | Constrói | Alta |
| Usuários finais | Usam no dia a dia | Usabilidade | Média |
| Azure | Infraestrutura | Restrições técnicas e custo | — |

### Evidências de discovery

| Data | Com quem | Formato | O que ficou provado |
|---|---|---|---|
| | | Entrevista (Mom Test) | |

> Requisito sem evidência atrás é hipótese, não requisito.

---

## 3. Personas

### Persona 1 — Joyce & Renata, Time de Custos e Nutrição

| Campo | Conteúdo |
|---|---|
| Contexto / background | Trabalham no escritório central do Grupo Saints, atendendo as 14 casas. Renata (nutricionista) garante qualidade e ingredientes junto aos chefs; Joyce (custos) certifica que as fichas técnicas estão na quantidade certa e acompanha o custo. Juntas cuidam da contagem de estoque, das fichas técnicas e do cálculo do custo teórico do cardápio. |
| Comportamentos | Fazem contagem física de estoque (semanal para itens principais, mensal completa); exportam dados "crus" do Everest e montam manualmente planilhas de custo; cruzam à mão o relatório de perdas do Compras para achar onde está o desperdício, o roubo ou o erro. |
| Dores | Gastam ~5 dias por mês montando planilhas manualmente a partir de exportações sem formatação do Everest; só descobrem uma perda concreta (ex.: R$ 6.000 em Grey Goose) no relatório de fim de mês, quando o prejuízo já ocorreu; não têm um dashboard que já cruze custo teórico × custo real automaticamente. |
| Objetivos | Reduzir o tempo gasto montando relatórios manuais; identificar rapidamente onde está o delta entre custo teórico e real, para agir antes que o prejuízo se acumule. |
| Cenário de uso | No fechamento mensal (hoje só sai perto do dia 15), abrir um dashboard que já mostra o CMV real vs. teórico por casa e por prato, sem precisar exportar e colar planilhas do Everest. |
| Frase-chave | "_Você clica lá exportar, aí vem um Excel cru, sem formatação, sem nada._" |

### Persona 2 — Sócio / Diretor Administrativo (papel de PO na entrevista)

| Campo | Conteúdo |
|---|---|
| Contexto / background | Sócio do Grupo Saints, responsável pela visão financeira consolidada das 14 casas — marcas do grupo: Boteco São Bento, Tartuferia San Paolo, Casa Yū, Tuy Bar Cocina, São Conrado Bar, Toca do Urso e Beer Island Tap House, em múltiplas unidades ([gruposaints.com.br](https://www.gruposaints.com.br/)); "Tulipa" citado na entrevista ainda não localizado no site, a confirmar. Participa das reuniões de resultado e fecha a DRE mensal do grupo. |
| Comportamentos | Liga para o RH quando quer saber quantos funcionários estão ativos numa casa; baixa ~15 planilhas do Everest (uma por restaurante) e monta manualmente a DRE consolidada todo início de mês; só questiona a escala de uma casa quando o custo de salário aparece inflado no fechamento. |
| Dores | Não enxerga em tempo real se uma casa está com a escala inchada — só descobre quando o prejuízo já apareceu na DRE (ex.: excesso de pessoal nas casas do Morumbi por ~3 meses após a Copa do Mundo); depende do RH e dos gerentes para qualquer dado de pessoal; monta a DRE manualmente, planilha por planilha. |
| Objetivos | Ter visibilidade rápida e centralizada de quem está ativo em cada casa e do custo de folha por casa, sem precisar pedir ao RH; ter uma DRE consolidada pronta, sem montagem manual. |
| Cenário de uso | Numa reunião de sócios, abrir o sistema e responder na hora "quantos funcionários ativos tem a casa X" e "como está o CMV desse mês", sem esperar o RH ou a equipe de custos prepararem um relatório. |
| Frase-chave | "_A gente só consegue depois ver o que aconteceu quando a gente vê que já deu merda._" |

---

## 4. Requisitos Funcionais (RF)

> ⚠️ **Rascunho v0.2, baseado só na Conversa 1 (sócio, papel de PO)** — ainda **não validado** com quem opera o processo no dia a dia (Joyce, Renata, Wellington — Conversa 2, pendente). O sócio confirmou *o quê* dói e *quanto* custa, mas admitiu não saber o passo a passo operacional ("isso eu explico depois, a Renata explica melhor"). Tratar RF03, RF05 e RF06 abaixo como hipótese de solução até a Conversa 2 confirmar o fluxo real — ver `00-customer-discovery.md`.

| ID | Requisito | MoSCoW | Sprint | Persona |
|---|---|---|---|---|
| RF01 | Upload do export de custo/estoque/compras do Everest | Must | | Persona 1 (Joyce/Renata) |
| RF02 | Cálculo e exibição do delta custo teórico × custo real, por casa | Must | | Persona 1 / Persona 2 |
| RF03 | Cadastro e consulta de funcionários ativos por casa (CRUD) | Must | | Persona 2 (Sócio/Diretor) |
| RF04 | Dashboard consolidado de custo (CMV real vs. teórico por casa) | Must | | Persona 2 |
| RF05 | Alerta de escala fora do padrão esperado por casa | Should | | Persona 2 |
| RF06 | Geração automática de DRE consolidada entre casas | Should | | Persona 2 |
| RF07 | Recomendação de quantidade de compra a partir do histórico de vendas | Could | | _(a definir — ADM/Compras)_ |

### Detalhamento

```
RF01 — Upload do export de custo/estoque/compras do Everest
Prioridade: Must
Descrição: Usuário (Joyce/Renata) faz upload de um arquivo (Excel/CSV) exportado do
Everest com dados de compras, estoque e custo do período. Sistema valida o formato
e armazena os dados associados à casa e ao período correspondentes.
Origem: entrevista com sócio do Grupo Saints em 01/09/2026 — "você clica lá exportar,
aí vem um Excel cru, sem formatação, sem nada" (hoje isso vira planilha manual).
Cobre a exigência mínima de "1 upload" do MVP da disciplina.

RF02 — Cálculo e exibição do delta custo teórico × custo real, por casa
Prioridade: Must
Descrição: A partir dos dados de RF01 (ficha técnica/custo teórico e
compra−venda+estoque/custo real), o sistema calcula o delta por casa e por
período e o exibe de forma que o usuário identifique onde está a maior perda,
sem precisar cruzar relatórios manualmente.
Origem: entrevista em 01/09/2026 — perda de R$ 6.000 em Grey Goose só detectada
no relatório de fim de mês; "eu preciso abrir o relatório da Joyce, [...] o de
compras, [...] a perda e tentar achar a ligação dos dois". Prioridade nº1
confirmada pelo cliente.

RF03 — Cadastro e consulta de funcionários ativos por casa (CRUD)
Prioridade: Must
Descrição: Sistema permite criar, listar, editar e desligar registros de
funcionários por casa, com status (ativo/inativo) visível sem depender de pedir
ao RH. Satisfaz a exigência de "1 CRUD completo" do MVP.
Origem: entrevista em 01/09/2026 — "só o RH que tem acesso a esses dados [...]
não é algo que ele [diretor] só abre e fala, deixa eu ver como está o Oscar
Freire hoje." Prioridade nº2 confirmada pelo cliente.
⚠️ Envolve dado pessoal de funcionário (LGPD) — detalhar com RH antes de sprint.

RF04 — Dashboard consolidado de custo (CMV real vs. teórico por casa)
Prioridade: Must
Descrição: Visão única, entre todas as casas, do CMV real vs. teórico do
período, substituindo a montagem manual de planilha "enxuta" que o cliente
hoje faz a partir dos dados brutos do Everest. Satisfaz a exigência de "1
dashboard" do MVP.
Origem: entrevista em 01/09/2026 — "quando você já tem isso [...] num dashboard,
elas só iriam ver se está certo".

RF05 — Alerta de escala fora do padrão esperado por casa
Prioridade: Should
Descrição: Sistema sinaliza quando o custo de folha de uma casa foge do
padrão esperado (métrica a definir com o cliente), antes que o problema só
apareça no fechamento mensal da DRE.
Origem: entrevista em 01/09/2026 — caso Morumbi: excesso de pessoal só
percebido ~3 meses depois, quando o número já tinha aparecido na DRE.
⚠️ Hipótese de solução — o limiar/regra do alerta ainda não foi validado com
o cliente nem com quem monta a escala hoje.

RF06 — Geração automática de DRE consolidada entre casas
Prioridade: Should
Descrição: Sistema consolida a DRE das 14 casas automaticamente a partir dos
dados já carregados, eliminando a montagem manual planilha por planilha.
Origem: entrevista em 01/09/2026 — "eu tenho que baixar 15 planilhas, jogar
pra minha planilha [...] e aí comer de novo"; o próprio cliente chamou de
"muito simples de fazer" (possível quick win, ver H4 no discovery).

RF07 — Recomendação de quantidade de compra a partir do histórico de vendas
Prioridade: Could
Descrição: Sistema sugere quantidade de compra por item, a partir do
histórico de vendas (Colibri/Everest), sinalizando picos e quedas sazonais
conhecidos.
Origem: entrevista em 01/09/2026 — "a gente não tem uma inteligência [...]
você parte do senso do chefe". O próprio cliente tratou como evolução
natural, não ponto de partida — ver H3 no discovery.
```

---

## 5. Requisitos Não Funcionais (RNF)

| ID | Categoria | Requisito (com métrica) | MoSCoW |
|---|---|---|---|
| RNF01 | Performance | 95% das requisições GET respondem em < 2s | Should |
| RNF02 | Disponibilidade | _(a confirmar — provável horário comercial, não 24/7; equipe de custos/RH trabalha em horário de escritório)_ | |
| RNF03 | Segurança | Segredos fora do código; HTTPS obrigatório; dado pessoal de funcionário (RF03) tratado conforme LGPD (acesso restrito a RH/sócios) | Must |
| RNF04 | Escalabilidade | ~10–15 usuários internos previstos (RH, custos, compras, sócios das 14 casas); sem pico de acesso conhecido — uso concentrado no fechamento mensal | Should |
| RNF05 | Backup | _(a confirmar com o cliente — dado é financeiro sensível, mas frequência/estratégia ainda não discutida)_ | |
| RNF06 | Usabilidade | Usuário identifica o delta de custo teórico × real de uma casa em até 3 cliques, sem precisar exportar ou formatar planilha (hoje leva ~5 dias/mês) | Must |

> RNF sem métrica não é testável. "Deve ser rápido" não conta.
> RNF02 e RNF05 estão deliberadamente incompletos — não foram perguntados ao cliente ainda; preencher na próxima conversa em vez de estimar sem evidência.

### Definições cloud (impactam custo e arquitetura)

| Dimensão | Resposta |
|---|---|
| Volume de dados (registros, GB/mês, crescimento) | Cliente tem ~16 anos de histórico total (Colibri/Everest), mas volume real do MVP depende do recorte de período que for exportado — **a confirmar**, não assumir a base histórica inteira |
| Usuários simultâneos e picos | ~10–15 usuários internos (RH, custos, compras, sócios); sem pico definido |
| Disponibilidade exigida (24/7? comercial?) | A confirmar — provável horário comercial |
| Sensibilidade dos dados (LGPD? financeiro? saúde?) | Sim, nos dois sentidos: dado financeiro do grupo (CMV, compras, DRE — não é dado pessoal, mas é sensível ao negócio) e dado pessoal de funcionário (RF03 — nome, horas trabalhadas, admissão/demissão), esse sim sob LGPD |
| Orçamento mensal | Azure for Students — US$ 100 / 12 meses |
| Integrações externas | Everest (API REST documentada, confirmada — ver `docs/discovery/everest-api.md`); Colibri (API existe mas de acesso mais restrito — dado já chega via Everest, ver `docs/discovery/colibri-api.md`); Dionísio (fora de escopo, sem API pública encontrada — ver `docs/discovery/dionisio-api.md`) |

---

## 6. User Stories

```
US01 — relacionada a RF01

Como <persona>,
quero <ação>,
para <benefício>.

Critérios de aceitação:
  DADO que <contexto>
  QUANDO <ação>
  ENTÃO <resultado>

  DADO que <contexto de erro>
  QUANDO <ação inválida>
  ENTÃO <erro esperado, com status code>
```

> INVEST: Independent, Negotiable, Valuable, Estimable, **Small (1–3 dias)**, Testable.
> 2 a 5 critérios GWT por story — eles viram os testes em `tests/`.

---

## 7. Priorização (MoSCoW)

| Nível | Fatia esperada | Requisitos |
|---|---|---|
| **Must** — o MVP | ~60% | |
| **Should** | ~20% | |
| **Could** | ~15% | |
| **Won't** (documentado) | ~5% | |

> Must = MVP. Só passe para Should quando todos os Must estiverem entregues.
> **Se tudo é Must, nada é Must.**

MVP mínimo exigido pela disciplina: **1 CRUD completo + 1 upload + 1 dashboard**, em 14 semanas (03/08 a 09/11).

---

## 8. Arquitetura Cloud

### Stack mínimo obrigatório

| Serviço | Uso no projeto | Justificativa |
|---|---|---|
| FastAPI | Backend REST | Python (linguagem do curso), validação Pydantic, docs automáticos |
| Azure App Service | Hospedagem PaaS | Deploy simples, SSL, auto-restart via `/health` |
| Azure SQL Database | Banco relacional | |
| Azure Blob Storage | Arquivos (CSV, PDF, imagem) | Binário no object storage, ponteiro no banco |
| React | Frontend + dashboard | |
| Docker + ACR | Containerização | |
| GitHub Actions | CI/CD | |

### Extras valorizados

- [ ] Redis Cache
- [ ] Key Vault
- [ ] Application Insights
- [ ] Azure Functions
- [ ] API Management

### Diagrama

_(inserir; ver `docs/02-arquitetura.md`)_

---

## 9. Restrições

| Tipo | Restrição |
|---|---|
| Prazo | 14 semanas — MVP até 09/11. Marcos intermediários (`ArquivosAula10/Aula_10_Entregas_AC1_AC2.md`): AC1 individual em 14/09 (feito), **AC2 em grupo em 21/09** — este documento de requisitos (com problema, cliente, RF, RNF, escopo negativo e esboço de arquitetura) é o entregável da AC2 |
| Orçamento | US$ 100 de crédito Azure for Students, sem cartão |
| Técnica | Stack obrigatório da disciplina; App Service F1 tem 60 min CPU/dia e não tem Always On |
| Equipe | _(tamanho, disponibilidade semanal)_ |
| LGPD | _(há dado pessoal? qual a base legal? há dado sensível?)_ |
| Cliente | _(disponibilidade para conversas ao longo do semestre)_ |

---

## 10. Glossário

| Termo | Definição |
|---|---|
| MVP | Minimum Viable Product — o conjunto Must |
| RF / RNF | Requisito Funcional / Não Funcional |
| GWT | Given-When-Then, formato dos critérios de aceitação |
| MoSCoW | Must / Should / Could / Won't have |
| DoD | Definition of Done |
| SLA | Service Level Agreement |
| PaaS | Platform as a Service |
| _(termo do domínio)_ | |

---

## Histórico de mudanças

| Data | Versão | O que mudou | Motivo |
|---|---|---|---|
| | 0.1 | Criação | Estrutura inicial |
| 13/09/2026 | 0.2 | Preenchidas Personas (seção 3), RF01–RF07 e RNF01–RNF06 | Baseado na Conversa 1 (`00-customer-discovery.md`) e na pesquisa técnica de Everest/Colibri/Dionísio (`docs/discovery/`). RF03, RF05 e RF06 marcados como hipótese de solução — pendente validação de fluxo operacional com Joyce, Renata e Wellington (Conversa 2, ainda não realizada) |
| 17/09/2026 | 0.2 | Corrigido nome do cliente de "Grupo Santos" para **Grupo Saints** em todos os docs; nomes das casas atualizados com base no site institucional ([gruposaints.com.br](https://www.gruposaints.com.br/)) | O nome "Grupo Santos" era erro de transcrição automática do áudio da entrevista (confirmado ao ouvir a resposta do cliente na transcrição, `Entrevista/entrevista_cliente.txt` linha 192); site oficial confirma "Grupo Saints" e lista as marcas: Boteco São Bento, Tartuferia San Paolo, Casa Yū, Tuy Bar Cocina, São Conrado Bar, Toca do Urso, Beer Island Tap House. "Tulipa", citado na entrevista, não aparece no site — sinalizado como pendente de confirmação |
