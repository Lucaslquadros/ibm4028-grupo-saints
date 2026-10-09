# Customer Discovery — registro das conversas

Preencher **antes** de escrever requisito. O ciclo é: hipótese → conversa → evidência → requisito.
O que não tiver evidência atrás volta a ser hipótese para a próxima conversa.

---

## Candidatos a cliente

| Candidato | Como chegar | Tem a dor? | Acessível? | Topa 3–4 conversas? | Status |
|---|---|---|---|---|---|
| | | | | | |

Onde procurar: rede próxima (negócio de família/amigos), comércio do bairro (padaria, pet shop, barbearia, oficina, clínica), ONGs e coletivos, dentro do IBMEC (secretaria, laboratórios, atlética, ligas, centro de carreiras), sua própria experiência (estágio, condomínio, esporte), profissionais do setor.

> Se depende de aprovação jurídica para conversar, procure outro.

---

## Hipóteses iniciais

| # | Quem tem o problema | Qual é a dor | Por que a solução atual não serve | Status |
|---|---|---|---|---|
| H1 | Joyce (custos), Renata (nutrição) e Compras (Wellington) | Não conseguem enxergar rápido o "delta" entre custo teórico (ficha técnica) e custo real (compra − venda + estoque); só descobrem uma perda (ex.: R$ 6.000 em Grey Goose) no relatório de fim de mês, quando já aconteceu | O Everest calcula os dados, mas só exporta "Excel cru, sem formatação" — obriga montagem manual de planilha e cruzamento manual com o relatório de perdas, levando ~5 dias/mês e saindo só perto do dia 15 | **Confirmada (Conversa 1)** — prioridade nº1 do cliente. Viabilidade técnica de integração verificada — ver [`docs/discovery/everest-api.md`](discovery/everest-api.md) |
| H2 | Sócios e diretor operacional | Não têm visibilidade rápida de quantos/quais funcionários estão ativos em cada casa nem se a escala está superdimensionada; só percebem quando o custo de salário já apareceu inflado na DRE (ex.: excesso de pessoal no Morumbi por ~3 meses após a Copa) | Esses dados existem, mas ficam isolados no RH; qualquer consulta depende de ligar e pedir a planilha, e a escala só é revista quando o problema já é visível no fechamento mensal | **Confirmada (Conversa 1)** — prioridade nº2 do cliente |
| H3 | ADM da casa, Compras e chef de cozinha | Pedidos de compra são baseados no "feeling" do chefe, não em dados — apesar de haver ~16 anos de histórico de vendas (Colibri) integrado ao estoque (Everest), não há previsão de demanda que ajuste o pedido a picos e quedas conhecidos (ex.: chopp triplica em final de Libertadores, receita cai 50% no carnaval) | O histórico existe e está tecnicamente integrado, mas ninguém cruza esse dado para recomendar quantidade de compra — a decisão continua manual e intuitiva | Confirmada (Conversa 1) — mencionada como evolução natural após resolver H1, não como ponto de partida. Viabilidade técnica verificada — ver [`docs/discovery/colibri-api.md`](discovery/colibri-api.md) |
| H4 | Sócio (visão financeira consolidada) | Gasta tempo todo início de mês baixando ~15 planilhas do Everest (uma por restaurante) e colando manualmente numa DRE consolidada | O Everest já tem o dado (DRE por casa), mas em formato bruto de ~10 mil linhas, sem uma visão enxuta e consolidada entre casas | Confirmada (Conversa 1) — o próprio cliente classificou como "muito simples de fazer", possível quick win |

---

## Roteiro (Mom Test)

Fale da vida da pessoa, não da sua ideia. Ouça 80%, fale 20%.

| Objetivo | Pergunta |
|---|---|
| Contexto | "Me conta como é um dia típico de trabalho seu." |
| Processo atual | "Me mostra como você faz isso hoje." |
| Frequência | "Quantas vezes por semana isso acontece?" |
| Último episódio | "Quando foi a última vez que deu problema? O que aconteceu?" |
| Custo | "Quanto tempo aquilo tomou? Quanto já custou em dinheiro?" |
| Tentativas | "O que você já tentou para resolver? Por que parou?" |
| Alcance | "Quem mais na equipe sofre com isso?" |
| Prioridade | "O que é mais urgente: velocidade, precisão ou facilidade?" |

**Não pergunte:** "você usaria um app que…", "você acha a ideia boa?", "você pagaria R$ X?", "isso é um problema, né?". Elogio não é evidência.

---

## Registro das conversas

### Conversa 1 — 01/09/2026 _(data aproximada, obtida do timestamp do arquivo de transcrição — confirmar com o grupo)_

| | |
|---|---|
| Com quem | Sócio do Grupo Saints (nome não identificado na transcrição), responsável pela gestão financeira/administrativa das ~14 casas do grupo. Marcas confirmadas no site institucional ([gruposaints.com.br](https://www.gruposaints.com.br/)): **Boteco São Bento** (Itaim, Vila Madalena, Campinas, Santo André), **Tartuferia San Paolo** (Morumbi, Oscar Freire), **Casa Yū** (Itaim Bibi), **Tuy Bar, Cocina** (Jardins, Shopping Morumbi — citado na transcrição como "TUI"), **São Conrado Bar** (Itaim, Pinheiros), **Toca do Urso** (Ribeirão Preto), **Beer Island Tap House** (Itaim, Vila Madalena, Campinas). ⚠️ "Tulipa", citado na entrevista como uma casa com sociedade diferente (paga 2,5% do faturamento ao escritório em vez de rateio integral), **não aparece no site institucional** — confirmar com o cliente se segue ativa, foi renomeada, ou não é destacada no site. |
| Duração | ~55 min (55:38, conforme transcrição) |
| Formato | Vídeo (chamada online; câmera do cliente desligada) |

**Perfil institucional (pesquisa complementar no site do grupo, [gruposaints.com.br](https://www.gruposaints.com.br/)):**

- Grupo se posiciona como especialista em **eventos corporativos** ("Eventos Corporativos com Propósito"), com ambientes versáteis para 20 a 500 pessoas — não é só operação de bar/restaurante para público espontâneo, o evento corporativo parece ser uma frente comercial relevante.
- **Mais de uma década de operação**; cita clientes como **XP Investimentos** entre parceiros/logos exibidos no site — sinal de porte e formalização do negócio.
- Site é majoritariamente institucional/comercial (formulário de orçamento para eventos) — não expõe operação interna, então não muda nada do discovery técnico já feito, só confirma nomes de marca e porte do grupo.
- Relevante para o projeto: se eventos corporativos forem uma linha de receita própria (não só o consumo de salão do dia a dia), pode valer perguntar na Conversa 2 se isso tem um fluxo de custo/estoque diferente do padrão (ex.: menus fechados por evento) — não assumir que é o mesmo processo do RF01/RF02 sem confirmar.

**Como resolve hoje (o processo, passo a passo):**

- **RH centralizado** (5 pessoas, para as 14 casas): admissão, demissão, controle de ponto/horas, férias e distribuição da caixinha (10%/13% de serviço). Só o RH acessa esses dados — qualquer outra pessoa (ex.: diretor operacional) precisa *pedir* a informação a eles.
- **Escala de cada casa**: montada pelo gerente local junto com o diretor operacional na abertura da casa. Não há revisão periódica formal ("não é um ritual") — a escala só é reavaliada quando o custo de salário aparece inflado na DRE mensal, quando um sócio "sobe o alerta".
- **Compras/estoque/custo** giram em torno de dois sistemas: **Everest** (ERP com módulos financeiro, vendas, compras e estoque) e **Colibri** (sistema de vendas integrado à maquininha e ao Everest, com ~16 anos de histórico).
- O **chef de cozinha** decide prato e quantidades "no feeling"; quando percebe que um insumo está acabando, avisa o **ADM da casa** (que cuida do estoque local), que então faz o pedido formal para **Compras**.
- **Joyce** (custos) e **Renata** (nutrição/qualidade) definem as fichas técnicas junto com os chefs, fazem contagem física de estoque (semanal para itens principais, mensal completa) e calculam o **custo teórico** do cardápio.
- **Compras** apura o **custo real** (compra − venda + estoque) e gera um relatório de perdas mensal.
- Todo fim de mês, Joyce/Renata baixam dados brutos do Everest ("Excel cru, sem formatação"), montam manualmente os relatórios de custo, e cruzam à mão com o relatório de perdas do Compras para achar o "delta" entre teórico e real.
- O sócio monta a **DRE consolidada** baixando ~15 planilhas do Everest (uma por restaurante) e colando manualmente numa planilha mestre, todo início de mês.

**Gambiarra em uso:** Excel/planilhas manuais alimentadas por exportação bruta do Everest ("Excel cru, sem formatação, sem nada"); telefonema para o RH pedindo a lista de funcionários ativos; DRE consolidada feita copiando e colando ~15 planilhas de restaurantes individuais numa planilha mestre.

**Último episódio concreto de problema:**

- Casas do Morumbi: escala foi inchada para a abertura de uma casa nova + período da Copa do Mundo. Quando o hype inicial baixou e a Copa terminou, o faturamento caiu mas o custo de salário não — o excesso de pessoal só foi percebido ~3 meses depois, quando o número já tinha aparecido na DRE ("a gente ficou um mês inteiro tomando no cu de faturamento e a gente tava inchado").
- Perda de R$ 6.000 em Grey Goose detectada apenas no relatório de perdas de fim de mês — quando a perda (roubo, desperdício ou erro de contagem) já havia ocorrido.

**Custo medido (tempo / dinheiro / cliente perdido):**

- CMV de ~30% do faturamento do grupo; compras somam ~R$ 45 milhões/ano, folha ~R$ 40 milhões/ano (as duas maiores linhas de custo, brigando pela primeira posição).
- Relatório de custo/perdas só sai por volta do dia 15 do mês seguinte — ~15 dias de atraso entre o problema acontecer e virar visível.
- Equipe de custos gasta cerca de **5 dias por mês** montando planilhas manualmente.
- Excesso de ~3 funcionários por ~2 meses nas casas do Morumbi (valor em R$ não quantificado pelo cliente, mas citado como perda relevante).

**O que já tentou e por que não deu certo:**

- O Everest já calcula custo teórico e centraliza compras/estoque/vendas, mas exporta dados "crus" (sem formatação, sem dashboard) — obriga trabalho manual de exportação e formatação toda vez.
- O RH já tem os dados de ponto/escala, mas de forma isolada — sem visão integrada para outros stakeholders (diretor, sócios).
- Nenhuma tentativa própria de automação/dashboard foi citada; o cliente vai buscar como benchmark o dashboard de outro grupo (Jangada), que usa um sistema similar ao Everest.

**Frases literais que valem citar:**

> "A gente só consegue depois ver o que aconteceu quando a gente vê que já deu merda."

> "Quando você vê já é tarde demais, já perdeu o dinheiro."

> "A gente aguarda 10 dias pra eles soltarem um relatório... ou seja, já perdeu 15 dias de você fazendo errado."

> "Você clica lá exportar, aí vem um Excel cru, sem formatação, sem nada."

> "16 anos de histórico é muita coisa... tá aí a mina de ouro, cara."

> "Hoje em dia você conta com o feeling do chefe para decidir o que vai comprar."

> "Você não ganha na margem dos funcionários, você ganha na venda dos produtos."

**Hipóteses confirmadas:**

- Falta de visibilidade rápida sobre dados operacionais (escala, delta de custo) leva a decisões tardias e prejuízo já consumado.
- Existe gambiarra ativa (planilhas manuais alimentadas por export cru), sinal forte de dor real, não hipotética.
- O problema mais caro para o negócio é o delta custo teórico × custo real em compras/estoque — maior prioridade do cliente do que a gestão de pessoal, embora as duas estejam próximas em peso.

**Hipóteses derrubadas:** Nenhuma — esta é a primeira conversa; não havia hipóteses formais registradas antes dela (ver seção "Hipóteses iniciais" acima, ainda vazia).

**Novas perguntas para a próxima conversa:**

- Com Joyce (custos) e Renata (nutrição): mapear o fluxo exato ficha técnica → contagem → cálculo do delta, passo a passo, com telas do Everest.
- Com Wellington (compras): como decide fornecedor, frequência real de pedidos emergenciais entre casas, e como seria a interface ideal de um "pedido recomendado" baseado em histórico.
- Ver o dashboard de referência do grupo Jangada (benchmark visual sugerido pelo próprio cliente).
- Quantificar em R$ o impacto do problema de escala/RH (o cliente só falou em número de funcionários, não em valor).
- ~~Confirmar se o Everest e o Colibri têm API ou exportação estruturada~~ — **respondido pela pesquisa técnica abaixo** para o Everest (tem API documentada); falta confirmar se está habilitada no contrato do cliente, e ainda falta checar o Colibri.
- Perguntar se o cliente conhece/usa o **Ever.BI** (módulo de BI nativo do Everest) — ver detalhe em [`docs/discovery/everest-api.md`](discovery/everest-api.md).

---

### Conversa 2 — _(data)_

_(mesma estrutura)_

---

## Validação técnica (pesquisa complementar)

> Pesquisa sobre os sistemas do cliente, feita fora da conversa direta com ele — usada para checar viabilidade técnica antes de comprometer o escopo. Cada sistema investigado a fundo vira um arquivo em `docs/discovery/`; esta tabela é o índice.

| Sistema | Usado para | Pergunta a responder | Status | Detalhe |
|---|---|---|---|---|
| Everest (ACOM Sistemas) | ERP: financeiro, compras, estoque | Tem API para extrair dados sem depender de export manual? | Confirmado — tem API REST documentada (Swagger); falta confirmar se está habilitada no contrato do cliente | [`docs/discovery/everest-api.md`](discovery/everest-api.md) |
| Ever.BI | BI nativo do Everest | Já cobre o delta custo teórico × real? Se sim, redefine a proposta de valor do projeto | Levantado durante a pesquisa do Everest — falta perguntar ao cliente se ele conhece/usa | [`docs/discovery/everest-api.md`](discovery/everest-api.md) |
| Colibri (NCR Colibri) | Sistema de vendas (PDV), integrado ao Everest, ~16 anos de histórico | Tem API própria, ou só alimenta o Everest? | Confirmado — tem API/SDK, mas acesso parece mediado por projeto/parceria (não self-service como o Everest); baixa prioridade porque o histórico de vendas já chega ao Everest | [`docs/discovery/colibri-api.md`](discovery/colibri-api.md) |
| CRM de reservas (Dionísio) | Gestão de reservas, já usa IA segundo o cliente | Fora do escopo priorizado (H1/H2) — investigar só se entrar no MoSCoW | Confirmado — sem API pública encontrada; baixíssima prioridade, cliente não identificou dor aqui | [`docs/discovery/dionisio-api.md`](discovery/dionisio-api.md) |

---

## Veredito: analgésico ou vitamina?

| Sinal | Confirmado? | Evidência |
|---|---|---|
| Acontece com alta frequência | Sim | Fechamento de custo é mensal; contagem de estoque dos itens principais é semanal |
| Custa tempo, dinheiro ou clientes | Sim | R$ 6.000 perdidos em Grey Goose num mês; CMV de 30%; ~R$ 45 milhões/ano em compras; ~5 dias de trabalho manual por mês só para montar planilhas |
| **Já existe gambiarra em uso** | Sim | Excel manual alimentado por export cru do Everest; ~15 planilhas coladas à mão para montar a DRE consolidada |
| Já tentaram resolver antes | Parcialmente | Everest e Colibri já centralizam os dados, mas o cliente usa só export manual, sem dashboard; cliente vai buscar benchmark no grupo Jangada. Pesquisa técnica revelou que o Everest tem um módulo de BI nativo (Ever.BI) que talvez já cubra parte disso — ainda não confirmado com o cliente se ele o conhece/usa (ver [`docs/discovery/everest-api.md`](discovery/everest-api.md)) |
| Existe alguém incomodado o bastante para ajudar | Sim | Sócio já se ofereceu para trazer a equipe (Joyce, Renata, Wellington) para entrevistas na sede |
| A pessoa devolve a ligação sem insistência | Sim | Entrevista realizada sem esforço de convencimento; o próprio cliente propôs os próximos passos |

**Conclusão:** Analgésico (com base na Conversa 1 — confirmar que se mantém após ouvir os usuários finais na Conversa 2). A dor é real, recorrente, mensurável em R$ e já tem gambiarra manual em uso — não é uma ideia que o cliente "acharia legal ter", é um custo que ele já sente todo mês. Prioridade nº1 confirmada pelo próprio cliente: delta custo teórico × custo real em compras/estoque. Prioridade nº2: visibilidade de escala/RH. Próximo passo natural (já sugerido pelo cliente) é entrevistar os usuários finais reais — Joyce, Renata e Wellington — antes de desenhar a solução, já que "essa solução não vai ser só usada por você, vai ser usada por eles."

Se a maioria ficou vazia, o problema é vitamina. Procure outro antes de escrever uma linha de código.
