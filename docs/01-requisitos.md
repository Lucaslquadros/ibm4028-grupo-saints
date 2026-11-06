# Documento de Requisitos

**IBM4028 — Projeto em Ciência de Dados IV | IBMEC CDIA | 2026.2**

| | |
|---|---|
| **Grupo** | _(nomes)_ |
| **Cliente (papel de PO)** | Grupo Saints (grupo de bares/restaurantes, [gruposaints.com.br](https://www.gruposaints.com.br/)). **Desde 06/11/2026 o cliente é caso de estudo, não PO ativo** — ver 1.7 |
| **Versão** | 0.9 — RF09 é Must; RF10 retirado; auditoria de uso da nuvem |
| **Última atualização** | 06/11/2026 |

## Ambiente em produção

| | |
|---|---|
| Aplicação (frontend) | https://zealous-river-0b6019910.6.azurestaticapps.net |
| API | https://app-projeto4-saints2026.azurewebsites.net |
| Documentação da API | https://app-projeto4-saints2026.azurewebsites.net/docs |
| Health check | https://app-projeto4-saints2026.azurewebsites.net/health |

> Este documento é a base da **AC2 (entrega de 21/09/2026)** e da **Entrega Parcial 1**, e é atualizado a cada sprint.
> Requisito que mudar aparece aqui **com o motivo** — mudança silenciosa é escopo fora de controle.
>
> Ao preencher, use a skill `requisitos-ibm4028` (está em `.claude/skills/`).

---

## 1. Visão Geral

### 1.1 Problema

> Formato: **"[Persona] precisa de [necessidade] porque [insight]."**

**Quem toca o custo de um negócio de alimentos precisa saber onde o custo real
divergiu do custo que deveria ter sido, porque hoje essa divergência só aparece
no fechamento do mês — quando o prejuízo já aconteceu e a causa já se perdeu.**

A dor foi validada no caso de origem (Grupo Saints, Conversas 1 e 2) e se agrava
no alvo do produto (Persona 3, pequeno negócio), que tem a mesma divergência
**sem** ter equipe de custos para investigá-la.

### 1.2 Como o problema é resolvido hoje

Com **planilha montada à mão**, todo mês, por pessoa. No caso de origem: a
equipe exporta três módulos do Everest (vendas, compras e materiais), cola em
Excel e cruza — cerca de **2 dias por casa**, com o resultado saindo só perto do
dia 15. Os exports são relatórios de impressão, não tabelas: trazem cabeçalho de
empresa, totais misturados com itens e hierarquia por indentação.

No alvo (pequeno negócio), não é resolvido: o dono olha o extrato, sente que a
margem apertou e decide compra "pelo senso".

> A gambiarra é a melhor evidência de que a dor é real. Aqui ela custa 2 dias por
> casa por mês e ainda assim chega tarde.

### 1.3 Impacto medido

Números do caso de origem, declarados pelo cliente nas Conversas 1 e 2.

| Dimensão | Situação atual | Meta com a solução |
|---|---|---|
| Tempo gasto | ~2 dias por casa por mês no fechamento; ~5 dias/mês do time de custos montando planilhas | Minutos: subir o export e ler o painel |
| Atraso da informação | Fechamento sai perto do dia 15 do mês seguinte | No mesmo dia em que o export existe |
| Custo da divergência | Ajuste de **−3,68 pp** entre CMV real e teórico num único mês, numa casa | Identificar e agir dentro do mês |
| Erros / retrabalho | Cruzamento manual de 3 relatórios; perdas descobertas só no fim do mês | Cruzamento automático, com o ajuste decomposto por grupo |

### 1.4 Objetivo do projeto

Transformar exports de ERP em um fechamento de CMV automático que mostra **onde**
o custo divergiu e **quanto comprar** no mês seguinte — sem montagem manual de
planilha e sem depender do ERP de nenhum fornecedor específico.

### 1.5 Escopo

**Dentro:**

- Cadastro de unidades (RF08)
- Upload de export de custo, em dois lados: teórico e real (RF01)
- Cálculo do CMV teórico × real, com o ajuste por grupo e total (RF02)
- Dashboard com fechamento, evolução mensal e itens que mais pesam (RF04)
- Recomendação de quantidade de compra a partir do histórico (RF07)
- Leitura de **três formatos**: dois relatórios do Everest e uma planilha
  genérica, que qualquer ERP exporta

**Fora (explicitamente):**

- Integração automática com API de ERP — o dado entra por arquivo
- Contagem de estoque e inventário: isso é do ERP do cliente, e duplicá-lo
  criaria duas fontes discordando sobre o mesmo estoque
- Registro de perdas e quebras (reconhecido como lacuna real — ver seção 7, Should)
- Gestão de pessoal, escala e folha (RF03/RF05)
- DRE consolidada entre múltiplas casas (RF06)
- Autenticação e multi-tenant — a API é pública nesta entrega
- Eventos, buffet e recebimento de mercadoria

### 1.6 Como o sucesso será medido

| Métrica | Alvo | Como foi verificado |
|---|---|---|
| O fechamento do mês sai do export cru sem intervenção manual | 100% dos meses carregados | 24 meses da casa piloto processados a partir dos arquivos reais |
| Tempo da operação manual substituída | de ~2 dias para < 5 min | Medido no fluxo de upload → painel |
| O cálculo não depende do ERP de origem | ≥ 2 formatos de origem distintos | 3 tradutores, provados em `tests/test_generalizacao.py` |
| O cálculo não depende do ramo do negócio | ≥ 2 taxonomias distintas de categoria | Farmácia e restaurante, sem categoria no código |
| O número é auditável por quem decide | método declarado na própria resposta da API | Campos `metodo`, `aviso` e `alerta_dado` em `recomendacao-compra` |

> Não entra como métrica de sucesso: "o cliente aprovou". O cliente parou de
> responder (1.7), e inventar aprovação que não houve seria o pior resultado
> possível deste documento.

### 1.7 Mudança de papel do cliente (06/11/2026)

O Grupo Saints **parou de responder** depois da Conversa 2 (Marcela,
operação/custos, 03/11/2026). A Conversa 3 e o CMV de compras de jul–ago/26,
pedidos em 03/11, não vieram. O cliente deixa de ser PO ativo e passa a ser
**caso de estudo**: o que ele já forneceu basta para provar o conceito, e o
escopo congela no que esse dado sustenta.

O que o cliente deixou provado, com evidência:

| Afirmação | Evidência |
|---|---|
| A dor existe e é caríssima em tempo | Conversa 1 e 2: ~2 dias por casa por mês montando o fechamento à mão, cruzando três módulos do Everest |
| A dor é de dado, não de software faltando | Os exports do Everest são relatórios de impressão, não tabelas — "vem um Excel cru, sem formatação, sem nada" |
| O sistema resolve a dor | 24 meses de CMV teórico e o fechamento de set/26 calculados a partir dos arquivos **reais**, sem tratamento manual |
| O resultado é acionável | set/26 acusou ajuste de **−3,68 pp** entre real e teórico — a divergência que a equipe leva dois dias para encontrar. Valor absoluto fora deste documento: ver nota de confidencialidade em 1.9 |

O que **não** foi validado, e por isso não é afirmado em nenhum lugar:

- Se o número de set/26 bate com a apresentação de fechamento da própria equipe
  (o gabarito nunca chegou).
- Se a equipe considera a tela utilizável no dia a dia (não houve teste de uso).
- RF03/RF05 (pessoal/escala) seguem como hipótese, nunca validados.

### 1.8 Tese de generalização

Sem PO ativo, a pergunta deixa de ser "o cliente aprovou?" e passa a ser "isto
serve a outro negócio?". A afirmação que o projeto sustenta é **específica**, e
foi escolhida por ser verificável:

> O cálculo de fechamento é agnóstico à origem do dado e ao ramo do negócio.
> Adaptar o sistema a um novo ERP é escrever **um tradutor**, não mexer na
> regra; e o conjunto de categorias que formam o CMV é **deduzido do dado**,
> não configurado.

Não afirmamos "serve para qualquer negócio" sem qualificação — um negócio que
não separe custo por grupo não é atendido, e integração automática com ERP
(API do Everest) está fora do escopo, por decisão registrada na seção 7.

Duas coisas tiveram que mudar no código para a tese parar de ser slide:

| Antes | Depois | Prova |
|---|---|---|
| Dois tradutores, os dois de relatórios do Everest | Terceiro tradutor (`leitores.ler_planilha`) lê tabela comum que qualquer ERP exporta; o formato é **detectado**, o usuário só declara o lado do fechamento | `tests/test_generalizacao.py` |
| `GRUPOS_CMV = ("ALIMENTOS", "BEBIDAS")` cravado no código | `crud.grupos_comparaveis` deduz: comparável é o grupo que os **dois** lados reportam | Na base real devolve exatamente ALIMENTOS e BEBIDAS — mesmo resultado, sem cravar o domínio |

A demonstração usa uma **farmácia** (`scripts/popular_demo_generico.py`): outro
ramo, outras categorias, planilha genérica em vez de Everest, e um grupo de
custo indireto (EMBALAGENS) que a dedução exclui sozinha do CMV.

### 1.9 Limitações conhecidas

Declaradas aqui para não serem descobertas numa pergunta de banca.

| Limitação | Detalhe |
|---|---|
| **Proveniência da DRE** | A DRE gerencial recebida em 23/10/2026 **não contém a casa nem o período** dentro do arquivo — só o timestamp do export no nome. O rótulo `2026-09` foi atribuído por quem rodou o importador. A evidência é circunstancial e razoável (exportada em 23/10, logo set/26 é o último mês fechado; a receita da DRE fica a ~1,6% da venda do cardápio do mesmo mês), mas **não é prova**. Um campo de casa/período no arquivo, ou a integração via API, resolveria |
| Uma casa real | O dado real cobre só o Boteco São Bento - Vila Madalena. O "consolidado entre casas" do RF04 é exercitado com a unidade de demonstração, não com 14 casas reais |
| Um mês de CMV real | 24 meses de teórico, 1 mês de real. A série de ajuste tem um ponto só |
| **Set/26 é o mês mais fraco da série** | A venda do cardápio em set/26 (o mês do fechamento que apresentamos) foi **75% da média** dos 24 meses, e abaixo do mínimo histórico anterior. Pode ser mês fraco real ou export tirado antes do fechamento — nada no arquivo diz. Consequências: **(a)** o CMV % não é afetado, porque é razão, e de fato 24,44% está em linha com todos os meses; **(b)** a receita da DRE equivale a ~94% da venda do cardápio desse setembro fraco, e a só ~71% da venda de um mês típico — ou seja, ela é compatível com setembro e **incompatível** com um mês normal, o que é evidência *a favor* de que os dois arquivos cobrem o mesmo período; **(c)** a previsão de demanda fica subestimada, e por isso `recomendacao-compra` emite `alerta_dado` quando detecta queda uniforme de volume em todo o catálogo |
| Dedução de grupos precisa dos dois lados | Uma casa que nunca enviou cardápio não tem como saber que "material de consumo" não é mercadoria; o sistema então soma todos os grupos com custo, em vez de aplicar uma taxonomia que não conhece (`tests/test_fechamento.py`) |
| Sem autenticação | A API é pública. Era RNF03 da Sprint 2 e não foi entregue |
| **Item é identificado por string de nome** | `LinhaCusto.nome` é a chave de fato do item, lida direto do export (`BOLINHO SB COSTELA 6 UN`, `COSTELA DO PECADO SB`). Se o nome mudar entre meses — e ERP permite editar cadastro —, a série temporal daquele produto **se parte em dois itens, em silêncio**: 12 meses viram 7 de um e 5 de outro, e `top-itens` e a recomendação de compra (RF07) passam a errar sem nenhum erro aparecer. Não há proteção hoje. Resolver exige um cadastro canônico com aliases, o que **duplicaria a chave de agregação** de três consultas já conferidas contra produção — por isso está registrado como risco, e não implementado às pressas. Não depende de foto (ver a retirada do RF10 em `10-anexos-de-imagem.md`) |

> **Nota de confidencialidade.** Este repositório é **público**. Os arquivos do
> cliente ficam em `dados_reais/` (no `.gitignore`), mas o cuidado vale também
> para os números extraídos deles: percentuais e pontos percentuais aparecem
> aqui, **valores absolutos de faturamento e custo de uma unidade identificada
> não**. Eles ficam na apresentação ao vivo e na tela da aplicação. O cliente
> cedeu os dados para o trabalho, não autorizou publicá-los — e parou de
> responder, então não há como pedir essa autorização.

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

> **Reposicionamento de 06/11/2026.** O alvo do produto passou a ser o **pequeno
> negócio** (Persona 3), e o Grupo Saints passou a ser o **caso de origem** —
> quem revelou o problema e cedeu a base real que prova a solução, não quem vai
> usá-la. Ver 1.7 e 1.8.
>
> As Personas 1 e 2 ficam preservadas porque é delas que vem toda a evidência de
> discovery: elas descrevem a dor num grupo com escritório central e equipe de
> custos. A Persona 3 é a mesma dor **sem** essa estrutura — e é por isso que o
> sistema importa mais para ela: a Joyce gasta 5 dias por mês montando planilha;
> o dono da padaria não tem Joyce.

### Persona 3 — Dono de pequeno negócio (alvo do produto)

| Campo | Conteúdo |
|---|---|
| Contexto / background | Dono de um ou dois estabelecimentos (padaria, restaurante, farmácia, distribuidora). Não tem equipe de custos nem controller: ele mesmo decide compra, confere nota e olha o resultado do mês. Usa um ERP simples ou um sistema de PDV que exporta planilha; ninguém no negócio sabe o que é BI |
| Comportamentos | Decide quanto comprar "pelo senso", olhando a prateleira; confere resultado no extrato bancário antes de olhar relatório; usa o contador para obrigação fiscal, não para gestão; mexe no preço de venda quando sente que a margem apertou, sem calcular |
| Dores | Não sabe se a margem caiu por preço de fornecedor, por desperdício ou por erro de ficha; compra demais e perde produto, ou compra de menos e perde venda; o relatório do ERP mostra o que aconteceu, nunca o que fazer; não tem tempo nem equipe para cruzar planilha |
| Objetivos | Saber onde está o dinheiro, por que mudou, e quanto comprar no mês que vem — em minutos, sem montar planilha e sem contratar ninguém |
| Cenário de uso | Fim do mês: exporta o relatório do ERP, sobe no sistema e vê o CMV, os itens que mais pesam e a sugestão de compra do mês seguinte. Decide a compra na mesma sessão |
| Frase-chave | _(hipótese — esta persona **não foi entrevistada**; ela é derivada da dor validada nas Personas 1 e 2, removendo a estrutura de escritório. Validá-la é o primeiro passo de qualquer continuação do projeto)_ |

> ⚠️ A Persona 3 é a única sem evidência de entrevista atrás. Isso está dito aqui
> de propósito: o documento proíbe requisito sem evidência, e inventar uma frase
> de cliente para ela seria pior que admitir a lacuna.

### Persona 1 — Joyce & Renata, Time de Custos e Nutrição _(caso de origem)_

| Campo | Conteúdo |
|---|---|
| Contexto / background | Trabalham no escritório central do Grupo Saints, atendendo as 14 casas. Renata (nutricionista) garante qualidade e ingredientes junto aos chefs; Joyce (custos) certifica que as fichas técnicas estão na quantidade certa e acompanha o custo. Juntas cuidam da contagem de estoque, das fichas técnicas e do cálculo do custo teórico do cardápio. |
| Comportamentos | Fazem contagem física de estoque (semanal para itens principais, mensal completa); exportam dados "crus" do Everest e montam manualmente planilhas de custo; cruzam à mão o relatório de perdas do Compras para achar onde está o desperdício, o roubo ou o erro. |
| Dores | Gastam ~5 dias por mês montando planilhas manualmente a partir de exportações sem formatação do Everest; só descobrem uma perda concreta (ex.: R$ 6.000 em Grey Goose) no relatório de fim de mês, quando o prejuízo já ocorreu; não têm um dashboard que já cruze custo teórico × custo real automaticamente. |
| Objetivos | Reduzir o tempo gasto montando relatórios manuais; identificar rapidamente onde está o delta entre custo teórico e real, para agir antes que o prejuízo se acumule. |
| Cenário de uso | No fechamento mensal (hoje só sai perto do dia 15), abrir um dashboard que já mostra o CMV real vs. teórico por casa e por prato, sem precisar exportar e colar planilhas do Everest. |
| Frase-chave | "_Você clica lá exportar, aí vem um Excel cru, sem formatação, sem nada._" |

### Persona 2 — Sócio / Diretor Administrativo _(caso de origem, papel de PO na entrevista)_

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
| RF08 | Cadastro e consulta de casas (unidades do grupo) — CRUD | Must | **Sprint 1** | Persona 2 (Sócio/Diretor) |
| RF01 | Upload do export de custo/estoque/compras do Everest | Must | **Sprint 1** | Persona 1 (Joyce/Renata) |
| RF02 | Cálculo e exibição do delta custo teórico × custo real, por casa | Must | **Sprint 1** | Persona 1 / Persona 2 |
| RF04 | Dashboard consolidado de custo (CMV real vs. teórico por casa) | Must | **Sprint 2** | Persona 2 |
| RF03 | Cadastro e consulta de funcionários ativos por casa (CRUD) | Must | **Adiado — pendente Conversa 2** | Persona 2 (Sócio/Diretor) |
| RF05 | Alerta de escala fora do padrão esperado por casa | Should | **Adiado — pendente Conversa 2** | Persona 2 |
| RF06 | Geração automática de DRE consolidada entre casas | **Won't** | **Fora de escopo desde 06/11** | Persona 2 (caso de origem) |
| RF07 | Recomendação de quantidade de compra a partir do histórico de vendas | **Must** | **Entregue 06/11** | Persona 3 (dono de pequeno negócio) |
| RF09 | Anexo de nota fiscal fotografada ao custo do período | **Must** | **Planejado — `10-anexos-de-imagem.md`** | Persona 3 |
| ~~RF10~~ | ~~Cadastro de produto com foto como âncora de identidade~~ | — | **Retirado em 06/11** — a foto não fazia o trabalho de identidade e o recurso duplicaria a agregação. Motivo em `10-anexos-de-imagem.md` | — |

> **Nota de retomada (09/10/2026):** RF03 e RF05 continuam como hipótese e ficam
> fora da Sprint 1 e da Sprint 2 — não dependem só de "ter tempo", dependem da
> Conversa 2 (Joyce, Renata, Wellington) validar o fluxo operacional e, no caso
> de RF03, o RH confirmar quais campos são realmente necessários antes de
> desenhar algo que toca dado pessoal (LGPD). Isso não bloqueia o restante: RF08,
> RF01, RF02 e RF04 cobrem o Problema 1 (custo/compras), que já foi validado
> diretamente pelo cliente na Conversa 1 e é prioridade nº1 dele. A Conversa 2
> deve ser agendada em paralelo à Sprint 1; se acontecer a tempo, RF03 entra
> como adição ao backlog da Sprint 2.

### Detalhamento

```
RF08 — Cadastro e consulta de casas (unidades do grupo)
Prioridade: Must
Descrição: CRUD de "casa" (unidade/restaurante do grupo) — nome, marca, cidade,
status (ativa/inativa). É a entidade base referenciada por RF01 (upload por
casa/período), RF02 (delta por casa) e RF04 (dashboard por casa); sem ela não
há como associar upload, custo ou dashboard a uma unidade específica.
Origem: não veio de uma fala literal do cliente, mas é inferido diretamente da
estrutura de todas as RF Must já validadas (ex.: "quero ver o delta... por
casa") — o grupo tem 14 casas e todo RF01/02/04 fala "por casa". Satisfaz a
exigência de "1 CRUD completo" do MVP, substituindo o Item placeholder.

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
Prioridade: Must (era Could até 06/11/2026)
Descrição: Para os itens que mais pesam no custo, o sistema devolve a demanda
esperada do mês seguinte a partir do histórico de venda já carregado, com
média móvel de 3 meses, ajuste de tendência e ajuste de sazonalidade, mais um
nível de confiança explicando o quanto confiar em cada número.
Origem: entrevista em 01/09/2026 — "a gente não tem uma inteligência [...]
você parte do senso do chefe". Subiu de Could para Must no reposicionamento
para pequeno negócio: a Persona 1 tem equipe para decidir compra, a Persona 3
não tem — é ela quem decide "pelo senso", e é aqui que o sistema deixa de
descrever o passado e passa a apoiar decisão.
Entregue: `GET /api/v1/metricas/recomendacao-compra`. Matemática isolada em
`app/services/previsao.py`, testada com números conferíveis à mão em
`tests/test_previsao.py`.
⚠️ Limites que a própria resposta da API declara:
  - **Não é machine learning.** É estatística descritiva, auditável de
    propósito: quem decide compra tem o direito de conferir o número.
  - **Não sabe o estoque atual** — o sistema lê relatórios de venda e compra,
    nunca uma contagem. A sugestão é um teto, assumindo estoque zero; quem
    compra subtrai o que tem na prateleira.
  - Não modela prazo de entrega, lote mínimo, validade, nem ruptura passada
    (item que vendeu pouco porque faltou enviesa a média para baixo).
  - **Avisa quando o dado de entrada é suspeito**: queda uniforme de volume em
    todo o catálogo costuma ser relatório incompleto, não mercado. O sistema
    não corrige — sinaliza, e quem decide julga.
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

Repriorizado em 06/11/2026, junto com o reposicionamento para pequeno negócio
(Persona 3). O que mudou e por quê está na última linha do histórico.

| Nível | Requisitos | Estado |
|---|---|---|
| **Must** — o MVP | RF08 (CRUD de unidade) · RF01 (upload do export) · RF02 (CMV teórico × real) · RF04 (dashboard) · RF07 (recomendação de compra) · **RF09 (anexo de nota fiscal)** | RF08/01/02/04/07 entregues; **RF09 planejado, não implementado** |
| **Should** | RNF03 autenticação · registro de perda com foto · decomposição do ajuste em contagem + perdas + não explicado · **tratamento da deriva de nome de item** (ver 1.9) | Nenhum entregue |
| **Could** | Alerta de variação de custo unitário por item · curva ABC de concentração de custo · OCR de nota fiscal | Nenhum iniciado |
| **Won't** (documentado) | RF03 (funcionários) · RF05 (alerta de escala) · **RF06 (DRE consolidada entre casas)** · integração via API do Everest | Fora de escopo, com motivo |

**Por que RF06 virou Won't:** consolidar a DRE de 14 casas é requisito de grupo
com escritório central — a Persona 3 tem uma ou duas unidades, e para ela o
recurso não existe. Mantê-lo como Should seria carregar escopo que o alvo do
produto não usa.

**Por que RF03 e RF05 seguem Won't:** nunca saíram de hipótese. Dependiam de uma
Conversa 3 que não aconteceu e, no caso de RF03, de o RH definir quais dados
pessoais entram (LGPD). Sem cliente respondendo, construir seria adivinhar.

**Por que a integração com a API do Everest é Won't:** ela só faz sentido para o
caso de origem. Para a Persona 3, que usa ERP simples, a planilha genérica é o
caminho — e é justamente o que sustenta a tese de generalização (1.8).

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
| Azure Static Web Apps | Hospedagem do frontend | CDN e certificado grátis, build/deploy próprio via GitHub Actions, separado do backend |
| Docker + ACR | Containerização | Opcional nesta fase — deploy do backend é por código (Oryx/buildpack), ver `docs/06-guia-deploy-azure.md` |
| GitHub Actions | CI/CD | |

### Extras valorizados

Auditoria completa de como cada recurso está sendo usado, com a fila de ajustes
ordenada por valor: **`09-uso-da-nuvem.md`**. Resumo das decisões:

- [ ] **Application Insights** — a fazer (nível 2 da fila). Hoje **nenhum log está habilitado** no App Service, então a regra 9 do projeto ("stack trace vai para o log") não tem destino
- [ ] **Key Vault** — a fazer (nível 3), depois da identidade gerenciada
- [ ] Azure Functions — só se o alerta de variação de custo por item sair do Could
- [x] ~~Redis Cache~~ — **recusado com motivo**: 10–15 usuários, uso concentrado no fechamento, nada a cachear
- [x] ~~API Management~~ — **recusado com motivo**: uma API, um consumidor

> Recusa documentada vale tanto quanto adoção. "Por que vocês não usaram Redis"
> tem resposta; "por que usaram" não teria.

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
| 09/10/2026 | 0.3 | Adicionado **RF08** (CRUD de Casa); preenchida coluna Sprint — RF08/RF01/RF02 → Sprint 1, RF04 → Sprint 2, RF06 → Sprint 2 (se sobrar tempo), RF03/RF05 → adiados, RF07 → fora do MVP atual | Retomada do projeto após período sem desenvolvimento de domínio (código ainda tinha só o placeholder `Item`). Conversa 2 (Joyce/Renata/Wellington) ainda não aconteceu; decisão foi priorizar o Problema 1 (custo/compras), já validado na Conversa 1, para não bloquear a Sprint 1 esperando a entrevista. RF08 nasceu da necessidade de uma entidade "casa" que todo RF Must já referenciava implicitamente |
| 03/11/2026 | 0.4 | RF01 passa a aceitar os **exports reais do Everest** em .xlsx, em dois tipos (`cardapio` = CMV teórico, `compras` = CMV real); RF02/RF04 passam a ser o **fechamento de CMV** (teórico × real × ajuste por grupo, evolução mensal, top itens). Detalhes em `07-fechamento-cmv.md` | Conversa 2 (Marcela, operação/custos) e análise dos exports reais: teórico e real vêm de relatórios separados (não existe o CSV com as duas colunas que o RF01 supunha), o CMV real já é pós-inventário, e a dor validada diretamente é o relatório de fechamento manual (~2 dias por casa). MVP focado numa casa piloto (Boteco São Bento - Vila Madalena) |
| 05/11/2026 | 0.5 | **RF04 entregue**: frontend React (Casas, Upload, Fechamento) publicado no Static Web Apps, consumindo a API de fechamento em produção. RF01/RF02/RF08 confirmados rodando ponta a ponta em produção (Azure SQL + Blob Storage) | Fechamento do MVP Must para a apresentação de 09/11. Falta só o CMV de compras real de jul–set/26 (pedido à Marcela em 03/11) para a demo com dado real completo |
| 06/11/2026 | 0.9 | **RF09 sobe para Must** (aposta de produto declarada, não requisito validado). **RF10 retirado** no mesmo dia em que foi criado: a foto não fazia o trabalho de identidade — o mapeamento de aliases fazia — e o recurso obrigaria a manter dois caminhos de agregação para sempre, para não quebrar números já conferidos contra produção. O problema que ele atacava (deriva de nome de item) virou **risco registrado em 1.9**, desacoplado de qualquer funcionalidade de foto | Com o prazo curto e sem cliente respondendo, a estratégia passou a priorizar flexibilidade: esperar validação é paralisia, então RF09 é apostado de propósito e isso está dito em vez de disfarçado. A retirada do RF10 veio de uma pergunta do próprio grupo — "por que a foto como âncora de identidade, isso não dificulta outras funcionalidades?" — e a resposta era sim: dificultava |
| 06/11/2026 | 0.8 | Adicionados **RF09** (anexo de nota fiscal fotografada) e **RF10** (cadastro de produto com foto como âncora de identidade), os dois como **Should** e **especificados sem implementar** em `10-anexos-de-imagem.md`. Criada a auditoria `09-uso-da-nuvem.md`, com a fila de ajustes de nuvem ordenada por valor. Seção 8 (extras valorizados) passa a registrar **recusa com motivo** de Redis e API Management | Decisão de priorizar funcionalidades que justifiquem o Blob Storage com **imagem**, em vez de aprofundar estatística no RF07 — o projeto é de conceito de nuvem, e Blob guardando só planilha subaproveita o recurso. A auditoria da configuração real achou quatro distâncias entre o que este documento afirmava e o que estava no ar, a pior delas sendo **nenhum log habilitado** apesar da regra 9. RF09 e RF10 entram como Should, não Must, porque nenhuma das duas foi validada com usuário e a Persona 3 segue não entrevistada |
| 06/11/2026 | 0.7 | **Reposicionamento para pequeno negócio.** Nova **Persona 3** (dono de pequeno negócio) como alvo do produto, com as Personas 1 e 2 rebaixadas a caso de origem. **RF07 sobe de Could para Must e é entregue** (`/api/v1/metricas/recomendacao-compra`). **RF06 vira Won't.** Seção 7 (MoSCoW), que estava vazia desde a criação do documento, preenchida com motivo para cada Won't. Nova limitação registrada em 1.9: set/26 é o mês mais fraco da série | Sem PO ativo, manter como alvo um grupo de 14 casas com escritório central era descrever um cliente que não existe mais para o projeto. O alvo passou a ser quem tem a mesma dor **sem** a estrutura: a Joyce gasta 5 dias por mês montando planilha, o dono da padaria não tem Joyce. Isso reordenou a prioridade — RF06 (DRE de 14 casas) deixou de fazer sentido e RF07 ("quanto comprar", que o cliente decide "pelo senso") virou o requisito que transforma o produto de relatório em apoio à decisão. A Persona 3 é declaradamente **não entrevistada**, e validá-la é o primeiro passo de qualquer continuação |
| 06/11/2026 | 0.6 | Cliente passa a **caso de estudo** (1.7); adicionadas a **tese de generalização** (1.8) e as **limitações conhecidas** (1.9), incluindo a proveniência não provada da DRE; registrado o ambiente em produção no topo | O Grupo Saints não respondeu ao pedido de 03/11 nem à Conversa 3, então o projeto não pode mais ser validado por um PO ativo — o que sobra como prova é a base real que ele já cedeu. Isso deslocou a pergunta de "o cliente aprovou?" para "isto serve a outro negócio?", e a resposta exigiu tirar do código o que era específico de restaurante: a lista `("ALIMENTOS", "BEBIDAS")` virou dedução a partir do dado, e um terceiro tradutor passou a aceitar planilha de qualquer ERP. A base real continua dando exatamente os mesmos números depois da mudança |
