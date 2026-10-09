# Briefing do cliente — para quem não foi à primeira entrevista

Este documento existe para colocar você no mesmo nível de quem já ouviu o cliente, antes da próxima conversa. Ele não pressupõe conhecimento de administração/gestão — todo termo do "mundo de empresa" é explicado na hora em que aparece. Se algo ainda ficar confuso, pergunta antes da entrevista, não durante.

Ele é um resumo em linguagem simples. Os documentos completos (com citações literais da entrevista, tabelas e critérios de priorização) estão em `docs/00-customer-discovery.md` e `docs/01-requisitos.md` — vale a pena ler depois, isso aqui é só a porta de entrada.

---

## 1. Quem é o cliente

O cliente é sócio do **Grupo Saints**, um grupo que é dono de **14 bares/restaurantes**, a maioria em São Paulo (nomes que vão aparecer: **Boteco São Bento**, **Tartuferia San Paolo**, **Casa Yū**, **Tuy Bar, Cocina** — na entrevista aparece como "TUI" —, **São Conrado Bar**, **Toca do Urso** e **Beer Island Tap House**; ver `docs/00-customer-discovery.md` para o mapa completo de unidades). Ele cuida da parte financeira e administrativa do grupo — não é ele quem trabalha no salão ou na cozinha, é ele quem olha os números de todas as casas juntas.

O grupo se posiciona também como especialista em **eventos corporativos** (site institucional: [gruposaints.com.br](https://www.gruposaints.com.br/)), com mais de uma década de operação e clientes como XP Investimentos entre os citados no site. Vale perguntar na próxima entrevista se eventos corporativos têm um fluxo de custo diferente do consumo normal de salão.

Ele **não é o usuário final** do que vamos construir. Ele é o "dono do problema e do orçamento", mas quem vai usar o sistema no dia a dia é a equipe dele (explicado na seção 3). Por isso a próxima entrevista é com essa equipe, não com ele de novo.

---

## 2. Glossário rápido (termos que vão aparecer o tempo todo)

| Termo | O que significa, em português simples |
|---|---|
| **Backoffice** | A parte "de escritório" da operação — financeiro, compras, RH. O oposto do salão/cozinha. |
| **ERP** | Um sistema de gestão único onde entram os dados de várias áreas do negócio (financeiro, estoque, compras). No caso do cliente, o ERP se chama **Everest**. |
| **PDV** | "Ponto de Venda" — o sistema por onde passa cada venda (tipo uma maquininha inteligente). No caso do cliente, o PDV se chama **Colibri**. |
| **CMV** | "Custo da Mercadoria Vendida" — quanto custou, em ingredientes, tudo que foi vendido. Se um prato custa R$10 pra fazer e é vendido por R$30, o CMV dele é 33%. É a métrica nº1 de quanto a comida "come" do lucro. |
| **Ficha técnica** | A "receita oficial" de um prato, com a quantidade exata de cada ingrediente (ex.: 100g de filé, 50g de arroz). Serve pra calcular quanto aquele prato *deveria* custar. |
| **Custo teórico** | Quanto um prato/período *deveria* ter custado, se ninguém desperdiçasse nada e a ficha técnica fosse seguida à risca. É uma conta feita em cima do papel. |
| **Custo real** | Quanto realmente saiu do estoque (comprado − vendido − o que sobrou). É o que de fato aconteceu, incluindo desperdício, roubo, erro de contagem. |
| **"O delta"** | A diferença entre custo teórico e custo real. Se o delta é grande, alguma coisa está vazando dinheiro (desperdício, roubo, prato malfeito). **Essa é a dor nº1 do cliente** — ver seção 4. |
| **DRE** | "Demonstrativo de Resultado do Exercício" — o resumo financeiro de um período (quanto entrou, quanto saiu, quanto sobrou). É tipo o "extrato de resultado" do mês de uma casa. |
| **Escala** | A lista de quais funcionários trabalham em cada casa, e em que função (quantos garçons, quantos na cozinha etc.). |
| **Folha (de pagamento)** | O total gasto com salário de funcionários num período. |
| **Caixinha / gorjeta / "10%/13% de serviço"** | O valor de gorjeta cobrado do cliente e depois dividido entre os funcionários. |
| **Período de experiência** | No Brasil, os primeiros ~90 dias de um funcionário novo, antes da empresa decidir se efetiva ele ou não. |
| **Rescisão** | O desligamento (demissão) de um funcionário. |
| **RH** | O setor que cuida de contratação, demissão, ponto/horas trabalhadas e férias dos funcionários — no caso do cliente, é uma equipe central de 5 pessoas que atende as 14 casas. |

---

## 3. Quem faz o quê (os personagens da história)

Você vai ouvir esses nomes/papéis na entrevista. Ninguém aqui é o cliente que já conversamos — são pessoas que trabalham para ele:

- **Joyce** — cuida de **custos**. É ela quem monta a ficha técnica junto com os chefs, faz contagem de estoque e calcula o custo teórico. Vamos entrevistá-la na próxima conversa.
- **Renata** — nutricionista, cuida da **qualidade** dos pratos com os chefs. Trabalha lado a lado com a Joyce (o próprio cliente disse "dá pra pensar nelas como uma pessoa só"). Também vamos entrevistá-la.
- **Wellington** — cuida de **compras**: negocia fornecedor, decide o que e quanto comprar, calcula o custo real. Também vamos entrevistá-lo.
- **ADM da casa** — uma pessoa por restaurante que cuida do estoque local (recebe mercadoria, ajuda na contagem, avisa a Compras quando falta algo).
- **Chef de cozinha** — decide o prato e pede reposição quando um ingrediente está acabando (hoje decide "no feeling", sem dado).
- **Gerente / Diretor operacional (Plínio)** — monta a escala de funcionários de cada casa.
- **RH (5 pessoas)** — únicos que hoje têm acesso a dados de quem está trabalhando em cada casa.

**Regra prática:** o cliente (sócio) é quem sente o problema no bolso, mas **Joyce, Renata e Wellington são quem vai usar o que a gente construir todo dia**. É por isso que a próxima entrevista é com eles, não com o sócio de novo — ele mesmo pediu isso: "essa solução não vai ser só usada por você, vai ser usada por eles."

---

## 4. As duas dores principais (nessa ordem de prioridade)

### Dor nº1 — "A gente só descobre o prejuízo depois que ele já aconteceu" (custo e compras)

Todo mês, o Everest calcula o custo teórico (o que *deveria* ter sido gasto) e o Wellington calcula o custo real (o que *de fato* foi gasto). A diferença entre os dois ("o delta") é onde está o desperdício, o roubo ou o erro.

O problema: hoje esse cálculo é **manual**. A Joyce e a Renata baixam uma planilha "crua" (sem formatação) do Everest, e passam **~5 dias por mês** montando relatório à mão para comparar com o que o Wellington apurou. O relatório só sai perto do **dia 15 do mês seguinte** — ou seja, quando um problema acontece, eles só ficam sabendo ~15 dias depois, quando já não dá pra fazer nada.

**Exemplo real que o cliente deu:** perderam **R$ 6.000 em uma garrafa de vodka (Grey Goose)** — só descobriram isso no relatório de fim de mês.

Números que mostram o tamanho do problema: o grupo gasta ~R$ 45 milhões/ano em compras, e o CMV (lembra do glossário?) é de ~30% do faturamento — cada ponto percentual que eles conseguem melhorar aqui vale muito dinheiro.

### Dor nº2 — "A gente só percebe que a escala está inchada quando o prejuízo já apareceu no balanço" (gestão de pessoas)

Quem sabe quantos funcionários estão trabalhando em cada uma das 14 casas é só o RH. Se um sócio quer saber isso, precisa **ligar e pedir**. A escala de cada casa é definida quando ela abre e quase nunca é revista — só quando o custo de salário aparece "inflado" na DRE do mês.

**Exemplo real que o cliente deu:** nas casas do Morumbi, contrataram gente a mais para a abertura de uma casa nova e para a Copa do Mundo (mais movimento esperado). Quando a Copa acabou e o movimento caiu, ninguém cortou a escala — **levaram ~3 meses para perceber** que estavam com funcionários a mais, só quando o número já tinha estourado na DRE. Ou seja: meses de prejuízo que já tinha acontecido e não dava mais pra evitar.

> Essas duas dores têm o mesmo formato: **o problema só aparece quando já é tarde para agir**. É essa a ideia central que o projeto tenta resolver — dar visibilidade *antes* do prejuízo, não um relatório *depois* dele.

---

## 5. Os sistemas que o cliente já usa

Vale saber que o cliente **não está começando do zero** — ele já tem sistemas que guardam esses dados, só não tem uma forma fácil de olhar pra eles:

- **Everest** — o ERP (lembra do glossário?) onde entram dados de compras, estoque, financeiro. Pesquisamos e confirmamos que ele **tem uma API** (uma forma de outros sistemas puxarem dados dele automaticamente, sem precisar de export manual). Isso é uma boa notícia técnica — dá pra pensar em automatizar a extração de dado, não só depender de planilha. Detalhe em `docs/discovery/everest-api.md`.
- **Colibri** — o PDV (registra cada venda). Também tem API, mas mais difícil de acessar (parece exigir virar "parceiro" do sistema). Boa notícia: os dados de venda que importam já chegam automaticamente dentro do Everest, então provavelmente não vamos precisar mexer direto no Colibri. Detalhe em `docs/discovery/colibri-api.md`.
- **Dionísio** — cuida de reservas usando IA (WhatsApp). O cliente disse que esse lado "já está bem resolvido" — ou seja, **não é uma dor**, é só contexto. Não é prioridade nenhuma agora.

---

## 6. O que já foi decidido com base na primeira conversa

Já demos um primeiro passo no documento de requisitos (`docs/01-requisitos.md`), definindo o que o sistema precisa fazer (nível bem inicial, ainda sujeito a mudar):

1. Permitir que a Joyce/Renata façam upload dos dados exportados do Everest.
2. Calcular e mostrar o "delta" (custo teórico × custo real) de forma visual, num painel — sem precisar cruzar relatórios na mão.
3. Mostrar quais funcionários estão ativos em cada casa, sem precisar ligar pro RH.
4. Um painel único juntando o custo de todas as 14 casas.

Isso ainda é um **rascunho**. Está marcado como pendente porque foi feito só com a visão do sócio — não temos ainda a visão de quem realmente opera esse processo todo dia. É exatamente isso que a próxima entrevista resolve.

---

## 7. O que ainda não sabemos (e por que sua presença na entrevista importa)

O sócio deu a visão de **negócio** (o que dói, quanto custa). Mas várias vezes na entrevista ele mesmo disse "isso a Renata explica melhor" — ele não conhece o passo a passo operacional no detalhe. Precisamos descobrir com Joyce, Renata e Wellington:

- Como é, na prática, o fluxo de criar uma ficha técnica → contar o estoque → calcular o delta? Quais telas do Everest eles usam?
- Como o Wellington decide quanto comprar hoje? O que ele olha antes de fazer um pedido?
- O que seria, pra eles, um "bom" jeito de ver esse dado — o que eles têm hoje que não serve, e o que sentem falta?
- Existe algo que o sócio descreveu errado ou incompleto, do ponto de vista de quem realmente faz o trabalho?

---

## 8. Como se comportar na entrevista (regra do "Mom Test")

Esse projeto segue um método chamado **Mom Test** — a ideia central é: **não pergunte se a pessoa "usaria" ou "gostaria" da sua ideia**. Pergunte sobre a vida e o trabalho dela como ela é hoje. As pessoas tendem a ser educadas e dizer que "sim, seria legal" mesmo que não seja verdade — isso não é evidência de nada.

Regras práticas para a entrevista:

- **Ouça 80%, fale 20%.** Não é hora de explicar o que a gente vai construir.
- Pergunte **"me mostra como você faz isso hoje"**, não "você acha que precisa de um sistema pra isso".
- Peça **exemplos concretos e recentes** ("quando foi a última vez que isso deu problema?"), não opiniões gerais.
- **Nunca pergunte:** "você usaria um app que...", "você acha a ideia boa?", "isso é um problema, né?". Um elogio educado não é evidência de nada.
- Se puder, **anote frases literais** que a pessoa disser — elas valem mais do que um resumo seu depois.

O roteiro completo de perguntas está em `docs/00-customer-discovery.md`, seção "Roteiro (Mom Test)" — vale dar uma olhada antes da entrevista.
