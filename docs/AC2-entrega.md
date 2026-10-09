# AC2 — Especificação inicial do escopo do projeto

**IBM4028 — Projeto em Ciência de Dados IV | IBMEC CDIA | 2026.2**

> Este documento monta, num único lugar, os 6 itens exigidos pela AC2. O conteúdo vem da
> entrevista com o cliente e do site institucional do Grupo Saints.

| Item exigido | Status |
|---|---|
| 1. O problema e quem sofre com ele | 🟢 Pronto |
| 2. O cliente ou usuário real | 🟢 Pronto |
| 3. Requisitos funcionais (user stories) | 🟡 Rascunho — RF03/RF05/RF06 seguem como hipótese até a Conversa 2, que fica para depois desta entrega |
| 4. Requisitos não funcionais | 🟢 Pronto — RNF02 e RNF05 fechados |
| 5. O escopo negativo | 🟢 Confirmado como no rascunho |
| 6. Esboço da arquitetura na Azure | 🟢 Pronto |
| Nomes do grupo, papéis, contato do cliente | 🟢 Pronto |

---

## Grupo e papéis

| Papel | Quem |
|---|---|
| Cliente / stakeholder | Diego Gordon — sócio do Grupo Saints, também sócio de outro bar, a Tulipa, com um grupo de sócios diferente. Contato: WhatsApp (11) 99500-4701 |
| Product Owner | Lucas |
| Scrum Master (sprint 1) | Pedro (rotativo — Otávio assume na próxima sprint) |
| Dev Team | Lucas, Pedro, Otávio |

**Tulipa** — outro bar (fora das 14 casas do Grupo Saints), com um grupo de sócios diferente, do qual Diego também faz parte. Registrado como oportunidade: se o piloto validar com o Grupo Saints, Diego pode levar a mesma solução para os sócios da Tulipa. Não faz parte do escopo do MVP.

---

## 🔴 Ainda em aberto

- [ ] Conversa 2 (Joyce, Renata, Wellington) fica para depois desta entrega — RF03/RF05/RF06 seguem como hipótese neste documento

---

## 1. O problema e quem sofre com ele

O **Grupo Saints** é dono de 14 casas (bares/restaurantes) em São Paulo e Ribeirão Preto —
Boteco São Bento, Tartuferia San Paolo, Casa Yū, Tuy Bar Cocina, São Conrado Bar, Toca do
Urso e Beer Island Tap House, entre outras unidades das mesmas marcas
([gruposaints.com.br](https://www.gruposaints.com.br/)). O grupo também atua com eventos
corporativos (posicionamento do próprio site), com mais de uma década de operação.

Duas dores, na ordem de prioridade dada pelo cliente:

**Problema 1 — custo e compras.** Joyce (custos) e Renata (nutrição) precisam identificar
rapidamente onde está a diferença entre o custo teórico de um prato (ficha técnica) e o
custo real (o que de fato saiu do estoque) **porque hoje essa diferença — "o delta" — só é
descoberta ~15 dias depois de o prejuízo já ter acontecido**, quando não há mais nada a
fazer. Exemplo real citado pelo cliente: perda de **R$ 6.000 numa garrafa de Grey Goose**,
detectada só no relatório de fim de mês.

**Problema 2 — gestão de pessoal.** O sócio e o diretor operacional precisam saber, a
qualquer momento, quantos funcionários estão ativos em cada casa e se a escala está
dimensionada corretamente **porque hoje esse dado só existe com o RH central, e a escala só
é revista quando o custo de salário já aparece inflado no fechamento mensal (DRE)**. Exemplo
real: nas casas do Morumbi, contrataram a mais para a abertura de uma casa nova e para a
Copa do Mundo; quando o movimento caiu, **levaram ~3 meses para perceber** o excesso de
pessoal.

As duas dores têm o mesmo formato: **o problema só aparece quando já é tarde para agir.**

**Quem sofre:**

| Quem | Como sofre |
|---|---|
| Joyce (custos) e Renata (nutrição) | Gastam **~5 dias por mês** montando planilhas manuais a partir de exportações "cruas" do Everest, para depois cruzar com o relatório de perdas do Compras |
| Wellington (compras) | Apura o custo real manualmente, sem visão automática do delta contra o teórico |
| Sócio / diretor administrativo | Monta a DRE consolidada colando ~15 planilhas à mão todo mês; não tem visibilidade de pessoal sem ligar para o RH |
| RH (5 pessoas para 14 casas) | É o único ponto de acesso a dados de pessoal — vira gargalo para qualquer consulta |

**Impacto medido:**

| Dimensão | Situação atual |
|---|---|
| Tempo gasto | ~5 dias/mês montando relatório de custo manualmente |
| Atraso na descoberta do problema | ~15 dias (relatório só sai perto do dia 15 do mês seguinte); ~3 meses no caso de escala |
| Custo | CMV ~30% do faturamento; ~R$ 45 milhões/ano em compras; ~R$ 40 milhões/ano em folha; caso concreto de R$ 6.000 perdidos numa garrafa |
| Fonte da evidência | Entrevista com o sócio em 01/09/2026 |

---

## 2. O cliente ou usuário real

| | |
|---|---|
| **Empresa** | Grupo Saints — grupo de 14 bares/restaurantes, com atuação também em eventos corporativos ([gruposaints.com.br](https://www.gruposaints.com.br/)) |
| **Papel do entrevistado** | Sócio do grupo, responsável pela visão financeira e administrativa consolidada das 14 casas — **não é o usuário final** do sistema. Atua como cliente/stakeholder do projeto (o PO no time é o Lucas) |
| **Como foi contatado** | Rede próxima — Diego é amigo do Lucas |
| **Primeira conversa** | 01/09/2026, ~55 min, chamada em vídeo |
| **O que saiu da primeira conversa** | Confirmação das duas dores (custo/compras e gestão de pessoal), priorização entre elas, números de impacto, mapa de sistemas já em uso (Everest, Colibri, Dionísio) |

**Usuários finais reais** (quem vai usar o sistema no dia a dia — o próprio cliente apontou
que a próxima entrevista precisa ser com eles, não com ele de novo):

- **Joyce** — custos: monta ficha técnica, faz contagem de estoque, calcula custo teórico
- **Renata** — nutricionista: qualidade dos pratos, trabalha lado a lado com a Joyce
- **Wellington** — compras: negocia fornecedor, decide quanto comprar, calcula custo real
- **ADM da casa** — estoque local por restaurante
- **RH central (5 pessoas)** — hoje é quem detém o dado de pessoal

**Conversa 2** (Joyce, Renata, Wellington) — 🔴 PENDENTE, ainda não realizada. É ela que
valida (ou derruba) as hipóteses de RF03, RF05 e RF06 abaixo.

---

## 3. Requisitos Funcionais (user stories)

> Formato trabalhado na Aula 02. Baseados na entrevista com o cliente —
> **RF03, RF05 e RF06 ainda não validados com quem opera o processo no dia a dia**, tratar
> como hipótese até a Conversa 2.

### US01 — Upload do export do Everest (RF01, Must)

Como Joyce ou Renata,
quero fazer upload do arquivo exportado do Everest com dados de custo/estoque/compras,
para não montar mais manualmente a planilha a partir do "Excel cru" todo mês.

Critérios de aceitação:
```
DADO que estou autenticada na área de upload
QUANDO envio um arquivo CSV/Excel exportado do Everest, associado a uma casa e período
ENTÃO o sistema valida o formato, armazena os dados e confirma o upload

DADO que envio um arquivo com formato inválido ou coluna obrigatória faltando
QUANDO clico em enviar
ENTÃO recebo erro (422) apontando o problema, e nada é importado
```

### US02 — Delta custo teórico × real (RF02, Must)

Como Joyce, Renata ou o sócio,
quero ver o delta entre custo teórico e custo real por casa e período,
para identificar onde está a perda sem cruzar relatórios manualmente.

Critérios de aceitação:
```
DADO que há dados de custo teórico e real carregados para uma casa e período
QUANDO acesso o painel de delta
ENTÃO vejo o valor do delta e os itens/categorias que mais contribuem para ele

DADO que faltam dados para o período consultado
QUANDO acesso o painel
ENTÃO vejo indicação clara do que falta, não um erro genérico
```

### US03 — Consulta de funcionários ativos por casa (RF03, Must — hipótese)

Como sócio ou diretor operacional,
quero consultar quais funcionários estão ativos em cada casa,
para não depender de ligar para o RH toda vez que preciso saber.

Critérios de aceitação:
```
DADO que estou autenticado com permissão adequada
QUANDO busco os funcionários ativos de uma casa
ENTÃO vejo a lista com nome, função e status (ativo/inativo)

DADO que tento cadastrar um funcionário com dado obrigatório faltando
QUANDO envio o formulário
ENTÃO recebo erro (422) apontando o campo
```
⚠️ Envolve dado pessoal (LGPD) — acesso restrito a RH/sócios; detalhar com RH antes de sprint.

### US04 — Dashboard consolidado de CMV (RF04, Must)

Como sócio,
quero um dashboard consolidado do CMV real vs. teórico entre as 14 casas,
para não montar mais manualmente a comparação planilha por planilha.

Critérios de aceitação:
```
DADO que há dados de custo carregados para múltiplas casas no mesmo período
QUANDO acesso o dashboard consolidado
ENTÃO vejo CMV real e teórico lado a lado, por casa, ordenável pelo maior delta
```

### US05 — Alerta de escala fora do padrão (RF05, Should — hipótese)

Como sócio,
quero ser avisado quando o custo de folha de uma casa fugir do padrão esperado,
para agir antes que o excesso de pessoal só apareça no fechamento da DRE.

⚠️ Hipótese de solução — o limiar/regra do alerta ainda não foi validado com o cliente.
Critérios de aceitação a definir após a Conversa 2.

### US06 — DRE consolidada automática (RF06, Should)

Como sócio,
quero uma DRE consolidada das 14 casas gerada automaticamente a partir dos dados já carregados,
para não precisar colar ~15 planilhas à mão todo mês.

Critérios de aceitação a detalhar — o próprio cliente chamou este item de "muito simples de
fazer" (possível quick win).

### US07 — Recomendação de quantidade de compra (RF07, Could)

Como Wellington (compras) ou ADM da casa,
quero uma sugestão de quantidade de compra baseada no histórico de vendas,
para não depender só do "feeling" do chef.

Tratado pelo cliente como evolução natural, não ponto de partida do MVP.

---

## 4. Requisitos Não Funcionais

| ID | Categoria | Requisito (com métrica) | MoSCoW |
|---|---|---|---|
| RNF01 | Performance | 95% das requisições GET respondem em < 2s | Should |
| RNF02 | Disponibilidade | Horário comercial, dias úteis (~8h–19h) — reflete o uso real hoje (equipe de custos/RH trabalha em horário de escritório); sem SLA de alta disponibilidade | Should |
| RNF03 | Segurança | Segredos fora do código; HTTPS obrigatório; dado pessoal de funcionário (RF03) tratado conforme LGPD, acesso restrito a RH/sócios | Must |
| RNF04 | Escalabilidade | ~10–15 usuários internos previstos (RH, custos, compras, sócios); sem pico de acesso conhecido — uso concentrado no fechamento mensal | Should |
| RNF05 | Backup | Backup automático diário via PITR (point-in-time restore) do Azure SQL, retenção de 7 dias — dado é financeiro sensível (CMV, compras, DRE) | Must |
| RNF06 | Usabilidade | Usuário identifica o delta de custo teórico × real de uma casa em até 3 cliques, sem exportar/formatar planilha (hoje leva ~5 dias/mês) | Must |

### Definições de cloud

| Dimensão | Resposta |
|---|---|
| Volume de dados | Cliente tem ~16 anos de histórico total (Colibri/Everest); volume real do MVP depende do recorte de período exportado — a confirmar |
| Usuários simultâneos | ~10–15 usuários internos, sem pico definido |
| Sensibilidade dos dados | Financeiro sensível ao negócio (CMV, compras, DRE) + dado pessoal de funcionário sob LGPD (RF03) |
| Orçamento | Azure for Students — US$ 100 / 12 meses |
| Integrações externas | Everest (API REST documentada); Colibri (API existe, acesso mais restrito, dado já chega via Everest); Dionísio (fora de escopo) |

---

## 5. O escopo negativo (o que **não** será feito nesta versão)

| Fora do escopo | Motivo |
|---|---|
| Integração direta com a API do Colibri (PDV) | Dado de vendas relevante já chega ao Everest pela integração nativa que o grupo já usa |
| Automação/gestão de reservas (Dionísio) | O próprio cliente disse que esse lado "já está bem resolvido" — não é uma dor |
| Recomendação de compra por IA/histórico (RF07) | Classificado pelo cliente como evolução natural, não ponto de partida — fica como Could, fora do MVP inicial |
| Cálculo/gestão completa de folha de pagamento, férias, rescisão | Sistema consulta status ativo/inativo por casa; não substitui o RH nem o processo de admissão/demissão |
| Fluxo de custo específico para eventos corporativos (menus fechados) | Linha de negócio identificada no site institucional, mas ainda não perguntada ao cliente — não assumir que segue o mesmo fluxo de RF01/RF02 sem confirmar |
| Integração em tempo real via API com o Everest | MVP nasce com upload manual do export (mesmo Excel que a Joyce já tira hoje); API fica para evolução futura, condicionada à liberação no contrato do cliente |
| Autenticação corporativa (SSO) | MVP usa autenticação simples (usuário/senha); SSO não é exigência da disciplina nem foi pedido pelo cliente |
| Aplicativo mobile nativo | Interface é web responsiva; não há app nativo iOS/Android |
| Disponibilidade 24/7 garantida | Uso concentrado em horário comercial (RNF02) — sem SLA de alta disponibilidade |
| Sobreposição com o Ever.BI (módulo de BI nativo do Everest) | Ainda não confirmado se o cliente conhece/usa — se ele já cobre o delta teórico×real, a proposta de valor do projeto precisa ser outra (ex.: visão cross-casas, alertas). Pauta obrigatória da Conversa 2 |

---

## 6. Esboço da arquitetura na Azure

Ponto de partida: a arquitetura de exemplo da disciplina (Static Web Apps / App Service +
Azure SQL + Blob Storage).

```
┌──────────────────┐        ┌───────────────────────┐        ┌────────────────────┐
│    Frontend      │        │  Backend (FastAPI)    │        │  Dados e Storage   │
│  React / browser │ HTTP   │  Azure App Service    │ HTTP   │  Azure SQL         │
│                  │ JSON   │                       │ TDS    │  Blob Storage      │
│ • interface      ├───────►│ • rotas / endpoints   ├───────►│                    │
│ • consome a API  │        │ • validação (Pydantic)│        │ • banco relacional │
│ • dashboard      │◄───────┤ • regras de negócio   │◄───────┤ • arquivos (export)│
└──────────────────┘        │ • autenticação        │        └────────────────────┘
                            └───────────┬───────────┘
                                        │ telemetria
                                        ▼
                            ┌───────────────────────┐
                            │ Application Insights  │
                            │ logs • métricas •     │
                            │ tracing • alertas     │
                            └───────────────────────┘
```

| Serviço | Uso no projeto | Por quê |
|---|---|---|
| FastAPI | Backend REST | Python, validação Pydantic, docs automáticos, exigência da disciplina |
| Azure App Service | Hospedagem do backend | Deploy simples, SSL, auto-restart via `/health` |
| Azure SQL Database | Banco relacional | Casas, funcionários, custos teórico/real, deltas |
| Azure Blob Storage | Arquivos exportados do Everest (CSV/Excel) | Binário fora do banco; ponteiro salvo no SQL |
| React | Frontend + dashboard | Consome a API, exibe delta e CMV consolidado |
| Docker + ACR | Containerização | Padrão de deploy da disciplina |
| GitHub Actions | CI/CD | Deploy automatizado, sem segredo de longa duração (OIDC) |

Decisões técnicas já tomadas: uv, SQLAlchemy síncrono, SQLite local → Azure SQL em produção,
versionamento `/api/v1/`.

Entidades de domínio previstas (a partir das RF acima): **Casa**, **Funcionário**,
**Upload/Período de custo**, **Item de custo (teórico × real)**. Ainda não modeladas no
código — que hoje usa uma entidade placeholder, aguardando este documento fechar.

---

## Fontes

- Entrevista com o sócio do Grupo Saints (Diego Gordon), 01/09/2026
- [gruposaints.com.br](https://www.gruposaints.com.br/) — site institucional do cliente
