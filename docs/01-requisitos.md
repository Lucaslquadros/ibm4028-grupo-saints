# Documento de Requisitos

**IBM4028 — Projeto em Ciência de Dados IV | IBMEC CDIA | 2026.2**

| | |
|---|---|
| **Grupo** | _(nomes)_ |
| **Cliente (papel de PO)** | Grupo Saints (grupo de bares/restaurantes, [gruposaints.com.br](https://www.gruposaints.com.br/)). **Desde 06/11/2026 o cliente é caso de estudo, não PO ativo** — ver 1.7 |
| **Versão** | 1.3 — RF11–RF13 entregues e publicados em 07/11 (ciclo `11-ciclo-explicacao-do-ajuste.md`) |
| **Última atualização** | 07/11/2026 |

## Ambiente em produção

| | |
|---|---|
| Aplicação (frontend) | https://zealous-river-0b6019910.6.azurestaticapps.net |
| API | https://app-projeto4-saints2026.azurewebsites.net |
| Documentação da API | https://app-projeto4-saints2026.azurewebsites.net/docs |
| Health check | https://app-projeto4-saints2026.azurewebsites.net/health — informa o **SHA do commit** publicado |

**Telas no ar:** Casas · Upload · Fechamento · Quanto comprar.
**Unidades em produção:** a casa piloto real (Boteco São Bento - Vila Madalena)
e quatro de demonstração, de ramos distintos, com "(DEMO)" no nome.

> Este documento é a base da **AC2 (entrega de 21/09/2026)** e da **Entrega Parcial 1**, e é atualizado a cada sprint.
> Requisito que mudar aparece aqui **com o motivo** — mudança silenciosa é escopo fora de controle.
>
> Ao preencher, use a skill `requisitos-ibm4028` (está em `.claude/skills/`).

---

## 1. Visão Geral

### 1.1 Problema

> Formato: **"[Persona] precisa de [necessidade] porque [insight]."**

**A analista de custos de uma rede de bares e restaurantes, e o sócio que decide
a partir do trabalho dela, precisam saber onde e por que o custo real divergiu
do custo que deveria ter sido, porque hoje essa divergência só aparece perto do
dia 15 do mês seguinte, depois de dois dias de planilha por casa — e mesmo
então como um número, sem a explicação.**

A dor foi validada no caso de origem (Grupo Saints, Conversas 1 e 2). O sistema
**encurta o diagnóstico** (do dia 15 para o dia 1–2 depois do inventário), mas
**não previne**: o CMV real depende do inventário do dia 30. Prevenção (delta
semanal, alertas) é roadmap.

### 1.2 Como o problema é resolvido hoje

Com **planilha montada à mão**, todo mês, por pessoa. No caso de origem: a
equipe exporta três módulos do Everest (vendas, compras e materiais), cola em
Excel e cruza — cerca de **2 dias por casa**, com o resultado saindo só perto do
dia 15. Os exports são relatórios de impressão, não tabelas: trazem cabeçalho de
empresa, totais misturados com itens e hierarquia por indentação.

> A gambiarra é a melhor evidência de que a dor é real. Aqui ela custa 2 dias por
> casa por mês e ainda assim chega tarde.

### 1.3 Impacto medido

Números do caso de origem, declarados pelo cliente nas Conversas 1 e 2.

| Dimensão | Situação atual | Meta com a solução |
|---|---|---|
| Tempo gasto | ~2 dias por casa por mês no fechamento; ~5 dias/mês do time de custos montando planilhas | Minutos: subir o export e ler o painel |
| Atraso da informação | Fechamento sai perto do dia 15 do mês seguinte | No mesmo dia em que o export existe |
| Custo da divergência | Sem inventário, compras × teórico oscila de −7,2 a +9,3 pp mês a mês na casa piloto (jun–dez/22) — o número de um mês não diz se houve desvio | Separar desvio de ritmo de estoque: CMV real com inventário, ou acumulado de vários meses sem ele |
| Erros / retrabalho | Cruzamento manual de 3 relatórios; perdas descobertas só no fim do mês | Cruzamento automático, com o ajuste decomposto por grupo |
| Entendimento do resultado | O ajuste chega como número; quem decide precisa da analista para interpretá-lo | Parágrafo em português que diz onde está a diferença e o que conferir (RF11) |

### 1.4 Objetivo do projeto

Transformar exports de ERP em um fechamento de CMV automático que **explica**
onde o custo divergiu e o que conferir, em linguagem que o sócio entenda, e
sugere **quanto comprar** no mês seguinte — sem montagem manual de planilha e
sem depender do ERP de nenhum fornecedor específico.

O público é definido pelo **dado que tem**, não pelo porte: operação com ficha
técnica cadastrada e inventário mensal, que exporta uma tabela com grupo, custo
e venda. O que o usuário precisa fornecer está em `07-fechamento-cmv.md`.

### 1.5 Escopo

**Dentro:**

- Cadastro de unidades (RF08)
- Upload de export de custo, em dois lados: teórico e real (RF01)
- Cálculo do CMV teórico × real, com o ajuste por grupo e total (RF02)
- Explicação do ajuste por regras: contribuição de cada grupo, subgrupos que existem nos dois lados, resumo e até 2 sugestões (RF11 — **entregue 07/11**)
- Fluxo guiado "Fechar o mês" com planilha-modelo (RF12 — **entregue 07/11**, Should)
- Tempo medido do primeiro envio ao resultado (RF13 — **entregue 07/11**, Should)
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
- Fluxo para quem não tem ERP (mini-ERP: cadastro de ficha técnica, contagem de estoque)
- Delta semanal e alertas durante o mês — exigem inventário parcial que não chega ao sistema
- Comparação teórico × real por **insumo** — exigiria a ficha técnica explodida em insumos, que o ERP não exporta nos relatórios recebidos
- Eventos, buffet e recebimento de mercadoria

### 1.6 Como o sucesso será medido

| Métrica | Alvo | Como foi verificado |
|---|---|---|
| O fechamento do mês sai do export cru sem intervenção manual | 100% dos meses carregados | 24 meses da casa piloto processados a partir dos arquivos reais |
| Tempo da operação manual substituída | de ~2 dias para < 5 min | **Entregue (RF13):** tempo de relógio no frontend, do primeiro envio ao resultado na tela. Não inclui exportar do ERP. Os ~2 dias são declarados pelo cliente, não medidos |
| O resultado é explicado, não só mostrado | Todo fechamento com os dois lados traz resumo e situação (acima / dentro / abaixo) | **Entregue (RF11):** `tests/test_explicacao.py`, e conferido em produção no fechamento de set/26 (`situacao: abaixo`) |
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
| O resultado é acionável | **Revisto em 10/11.** O −3,68 pp de set/26 é compras × teórico, **não** CMV real: falta a variação de estoque (ver `07-fechamento-cmv.md`, "A DRE é compras, não consumo"). Com as DREs de jun–dez/22 da planilha da equipe, o acumulado de 7 meses dá **+0,48 pp** (ALIMENTOS +5,14, BEBIDAS −3,14) — essa é a leitura acionável hoje: alimentos é onde procurar. Valor absoluto fora deste documento: ver nota de confidencialidade em 1.9 |

O que **não** foi validado, e por isso não é afirmado em nenhum lugar:

- O CMV real de qualquer mês: falta o inventário valorizado (estoque inicial e
  final), e o time confirmou em 10/11 que não tem acesso a ele. A planilha de
  fechamento da equipe chegou e foi usada como **método** (ver `07`).
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

**Genérico no formato, não no público** (decisão de 07/11/2026). Provar que a
regra não depende do ERP nem do ramo **não** exige mudar de persona. O sistema
serve a qualquer operação que tenha **ficha técnica e inventário mensal** —
essa é a fronteira, e ela está escrita em `07-fechamento-cmv.md`, "O que o
usuário precisa fornecer". Um pequeno negócio sem esses dois controles não é
atendido, por mais que tenha o mesmo porte das DEMO.

Duas coisas tiveram que mudar no código para a tese parar de ser slide:

| Antes | Depois | Prova |
|---|---|---|
| Dois tradutores, os dois de relatórios do Everest | Terceiro tradutor (`leitores.ler_planilha`) lê tabela comum que qualquer ERP exporta; o formato é **detectado**, o usuário só declara o lado do fechamento | `tests/test_generalizacao.py` |
| `GRUPOS_CMV = ("ALIMENTOS", "BEBIDAS")` cravado no código | `crud.grupos_comparaveis` deduz: comparável é o grupo que os **dois** lados reportam | Na base real devolve exatamente ALIMENTOS e BEBIDAS — mesmo resultado, sem cravar o domínio |

A demonstração está **em produção**, com **quatro ramos** carregados por
`scripts/popular_demo_generico.py` a partir de `exemplos/`:

| Unidade (DEMO) | Ramo | CMV teórico | CMV real | Ajuste set/26 | Grupos deduzidos | Indireto excluído |
|---|---|---|---|---|---|---|
| Drogaria Central | Farmácia | 47,89% | 50,55% | +2,66 pp (PERFUMARIA) | MEDICAMENTOS, PERFUMARIA | EMBALAGENS |
| Padaria Sao Jose | Padaria | 38,58% | 39,97% | +1,39 pp (FRIOS) | CONFEITARIA, FRIOS, PANIFICACAO | MATERIAL DE LIMPEZA |
| Pizzaria Bella | Pizzaria | 32,40% | 31,60% | −0,80 pp (dentro, com compensação) | BEBIDAS, PIZZAS, SOBREMESAS | DESCARTAVEIS |
| Distribuidora Horizonte | Atacado de bebidas | 75,83% | 79,32% | +3,49 pp (CERVEJAS) | CERVEJAS, DESTILADOS, NAO ALCOOLICOS | LOGISTICA |

> **Refeito em 10/11/2026.** Até aqui o lado real das DEMO era uma cópia do
> teórico multiplicada por um fator único por mês (+9% em set/26 em **todos** os
> grupos de **todas** as empresas), com a mesma venda nos 6 meses. O fechamento
> saía, mas não tinha o que explicar: nenhum grupo concentrava o desvio, não
> havia compensação nem série para o RF07. Agora o real sai de **estoque inicial
> + compras − estoque final** por item, as vendas variam por mês e cada desvio
> tem causa nomeada (perda, ficha desatualizada, compra não lançada, erro de
> contagem que volta no mês seguinte) — ver `exemplos/README.md`. Valores acima
> conferidos numa API local; a produção só muda quando o script for rodado lá.

Quatro taxonomias, **nenhuma conhecida pelo código**, e em cada uma o custo
indireto é excluído do CMV pela própria dedução. O par Pizzaria (32%) ×
Distribuidora (76%) é o mais eloquente: margem de restaurante contra margem de
atacado, no mesmo cálculo, sem configuração.

Dado fictício e rotulado como tal. O fechamento da casa piloto real foi
conferido **depois** da carga e segue idêntico — dado fictício ao lado de dado
real não pode mexer nele.

Por que existem: sem os dados das outras casas do Grupo Saints para a
apresentação, o grupo precisava de outros exemplos para mostrar que a solução é
genérica. Elas provam **formato e regra**, não mercado — nenhum desses ramos é
cliente ou foi entrevistado.

### 1.9 Limitações conhecidas

Declaradas aqui para não serem descobertas numa pergunta de banca.

| Limitação | Detalhe |
|---|---|
| ~~**Proveniência da DRE**~~ | ~~A DRE recebida em 23/10 não contém a casa nem o período.~~ **Confirmado pelo time em 10/11**: é da Vila Madalena, set/26. O arquivo segue sem esses campos; para os próximos envios, quem declara continua sendo o usuário |
| Uma casa real | O dado real cobre só o Boteco São Bento - Vila Madalena. O "consolidado entre casas" do RF04 é exercitado com a unidade de demonstração, não com 14 casas reais |
| **Nenhum mês de CMV real** | O lado real disponível é só **compras** (DRE), nunca consumo: falta o inventário. Há DRE de set/26 e, nas abas `ENTRADA` da planilha da equipe, de jun–dez/22 (importáveis com `scripts/importar_dre_historica.py`). Com elas o acumulado de 7 meses fica conclusivo; set/26 sozinho, não |
| **Set/26 é o mês mais fraco da série** | A venda do cardápio em set/26 (o mês do fechamento que apresentamos) foi **75% da média** dos 24 meses, e abaixo do mínimo histórico anterior. Pode ser mês fraco real ou export tirado antes do fechamento — nada no arquivo diz. Consequências: **(a)** o CMV % não é afetado, porque é razão, e de fato 24,44% está em linha com todos os meses; **(b)** a receita da DRE equivale a ~94% da venda do cardápio desse setembro fraco, e a só ~71% da venda de um mês típico — ou seja, ela é compatível com setembro e **incompatível** com um mês normal, o que é evidência *a favor* de que os dois arquivos cobrem o mesmo período; **(c)** a previsão de demanda fica subestimada, e por isso `recomendacao-compra` emite `alerta_dado` quando detecta queda uniforme de volume em todo o catálogo |
| Dedução de grupos precisa dos dois lados | Uma casa que nunca enviou cardápio não tem como saber que "material de consumo" não é mercadoria; o sistema então soma todos os grupos com custo, em vez de aplicar uma taxonomia que não conhece (`tests/test_fechamento.py`) |
| **Subgrupos de cardápio e de compras são taxonomias diferentes** | No Everest, o cardápio agrupa por categoria de **venda** (PETISCOS, CHOPP) e a DRE por categoria de **insumo** (BOVINOS, HORTIFRUTI). Abaixo do grupo, só é possível comparar teórico × real quando o nome coincide (ex.: CHOPP). Nas DEMO os subgrupos são iguais nos dois lados, então a comparação parece completa lá e quase vazia na casa real. RF11 declara isso na tela em vez de inventar a granularidade |
| **Nomes que diferem só no singular/plural não são comparados** | Achado ao conferir o RF11 em produção, 07/11: na casa piloto o lado teórico traz `AGUAS`, `ENERGETICOS`, `VINHOS`, `SOBREMESA` e o lado real traz `AGUA`, `ENERGETICO`, `VINHO`, `SOBREMESAS`. São quatro pares que um humano leria como o mesmo subgrupo e que o sistema trata como oito categorias sem par. A padronização do P0 resolve caixa e espaço, **não** flexão. Deixado assim de propósito: casar `AGUAS` com `AGUA` é heurística de linguagem, e errar nela produz um desvio inventado — pior do que a lacuna. O caminho correto é padronizar no cadastro do ERP ou mapear explicitamente, não adivinhar |
| ~~**O sistema não confere se o lado real é pós-inventário**~~ | **Tratado em 10/11:** cada upload do lado real tem uma base (`compras`, `consumo`, `declarada`). A DRE do Everest é `compras` e a tela a chama de "Compras", não de "Real"; o RF11 diz que o mês não é conclusivo. Continua sem conferência a planilha genérica só com `custo` (`declarada`) |
| ~~**Nome de grupo sensível a maiúsculas**~~ | ~~`Alimentos` num lado e `ALIMENTOS` no outro viram grupos distintos, e o grupo sai do CMV sem erro.~~ **Corrigido em 07/11** (P0 de `11-ciclo-explicacao-do-ajuste.md`): os três tradutores padronizam nome de grupo e subgrupo na leitura — maiúsculas e espaços internos colapsados, acento mantido. Vale para uploads novos; os já carregados vieram todos em maiúsculas |
| Sem autenticação | A API é pública. Era RNF03 da Sprint 2 e **não foi entregue** — é a lacuna mais séria do trabalho |
| Observabilidade pela metade | Os logs do App Service foram ligados em 06/11/2026 (antes disso a regra 9 não tinha destino), mas **Application Insights não existe**: não há série histórica de requisição, latência e falha. Nível 2 da fila em `09-uso-da-nuvem.md` |
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

> **Decisão de 07/11/2026: voltam as Personas 1 e 2.** Em 06/11 o alvo tinha
> passado para o pequeno negócio (Persona 3), numa tentativa de generalizar a
> solução para mais de um negócio. Na revisão de 07/11 ficou claro que
> generalizar o **formato do dado** não exige mudar de **público**, e que a
> Persona 3 tinha dois problemas: nunca foi entrevistada, e o cálculo exige
> ficha técnica e inventário mensal — controles que justamente o pequeno
> negócio costuma não ter. Ver 1.8 e `11-ciclo-explicacao-do-ajuste.md`, D1–D2.
>
> | Persona | Papel no sistema | Sabe custos? | Evidência |
> |---|---|---|---|
> | **1 — Analista de custos** | **Alimenta**: sobe os exports e confere o cálculo | É especialista | Conversa 2 |
> | **2 — Sócio / diretor** | **Decide**: lê o fechamento explicado | Conhece DRE e CMV como número, não a mecânica de ficha e inventário | Conversa 1 |
> | 3 — Dono de pequeno negócio | Nenhum neste ciclo — hipótese de mercado futuro | Hipótese, sem entrevista: em geral não — tende a confundir compras do mês com custo do mês e não faz inventário | **Nenhuma** |
>
> O texto em linguagem simples do RF11 é escrito **para a Persona 2**. A
> Persona 1 não precisa dele, mas é quem garante que o dado de entrada está certo.

### Persona 1 — Joyce & Renata, Time de Custos e Nutrição _(usuária principal — alimenta o sistema)_

| Campo | Conteúdo |
|---|---|
| Contexto / background | Trabalham no escritório central do Grupo Saints, atendendo as 14 casas. Renata (nutricionista) garante qualidade e ingredientes junto aos chefs; Joyce (custos) certifica que as fichas técnicas estão na quantidade certa e acompanha o custo. Juntas cuidam da contagem de estoque, das fichas técnicas e do cálculo do custo teórico do cardápio. |
| Comportamentos | Fazem contagem física de estoque (semanal para itens principais, mensal completa); exportam dados "crus" do Everest e montam manualmente planilhas de custo; cruzam à mão o relatório de perdas do Compras para achar onde está o desperdício, o roubo ou o erro. |
| Dores | Gastam ~5 dias por mês montando planilhas manualmente a partir de exportações sem formatação do Everest; só descobrem uma perda concreta (ex.: R$ 6.000 em Grey Goose) no relatório de fim de mês, quando o prejuízo já ocorreu; não têm um dashboard que já cruze custo teórico × custo real automaticamente. |
| Objetivos | Reduzir o tempo gasto montando relatórios manuais; identificar rapidamente onde está o delta entre custo teórico e real, para agir antes que o prejuízo se acumule. |
| Cenário de uso | No fechamento mensal (hoje só sai perto do dia 15), abrir um dashboard que já mostra o CMV real vs. teórico por casa e por prato, sem precisar exportar e colar planilhas do Everest. |
| Frase-chave | "_Você clica lá exportar, aí vem um Excel cru, sem formatação, sem nada._" |

### Persona 2 — Sócio / Diretor Administrativo _(tomador de decisão — lê o resultado)_

| Campo | Conteúdo |
|---|---|
| Contexto / background | Sócio do Grupo Saints, responsável pela visão financeira consolidada das 14 casas — marcas do grupo: Boteco São Bento, Tartuferia San Paolo, Casa Yū, Tuy Bar Cocina, São Conrado Bar, Toca do Urso e Beer Island Tap House, em múltiplas unidades ([gruposaints.com.br](https://www.gruposaints.com.br/)); "Tulipa" citado na entrevista ainda não localizado no site, a confirmar. Participa das reuniões de resultado e fecha a DRE mensal do grupo. |
| Comportamentos | Liga para o RH quando quer saber quantos funcionários estão ativos numa casa; baixa ~15 planilhas do Everest (uma por restaurante) e monta manualmente a DRE consolidada todo início de mês; só questiona a escala de uma casa quando o custo de salário aparece inflado no fechamento. |
| Dores | Não enxerga em tempo real se uma casa está com a escala inchada — só descobre quando o prejuízo já apareceu na DRE (ex.: excesso de pessoal nas casas do Morumbi por ~3 meses após a Copa do Mundo); depende do RH e dos gerentes para qualquer dado de pessoal; monta a DRE manualmente, planilha por planilha. |
| Objetivos | Ter visibilidade rápida e centralizada de quem está ativo em cada casa e do custo de folha por casa, sem precisar pedir ao RH; ter uma DRE consolidada pronta, sem montagem manual. |
| Cenário de uso | Numa reunião de sócios, abrir o sistema e responder na hora "quantos funcionários ativos tem a casa X" e "como está o CMV desse mês", sem esperar o RH ou a equipe de custos prepararem um relatório. |
| Frase-chave | "_A gente só consegue depois ver o que aconteceu quando a gente vê que já deu merda._" |

**Como o sistema atende a Persona 2 neste ciclo:** ela não monta planilha nem
interpreta pontos percentuais. Recebe o fechamento com um parágrafo — "onde
ficou a diferença, e o que conferir" — e decide a partir dele. A visibilidade de
pessoal (RF03/RF05) continua fora: nunca saiu de hipótese.

### Persona 3 — Dono de pequeno negócio _(hipótese de mercado futuro — não é alvo desde 07/11)_

| Campo | Conteúdo |
|---|---|
| Contexto / background | Dono de um ou dois estabelecimentos (padaria, restaurante, farmácia, distribuidora). Não tem equipe de custos nem controller: ele mesmo decide compra, confere nota e olha o resultado do mês. Usa um ERP simples ou um sistema de PDV que exporta planilha; ninguém no negócio sabe o que é BI |
| Comportamentos | Decide quanto comprar "pelo senso", olhando a prateleira; confere resultado no extrato bancário antes de olhar relatório; usa o contador para obrigação fiscal, não para gestão; mexe no preço de venda quando sente que a margem apertou, sem calcular |
| Dores | Não sabe se a margem caiu por preço de fornecedor, por desperdício ou por erro de ficha; compra demais e perde produto, ou compra de menos e perde venda; o relatório do ERP mostra o que aconteceu, nunca o que fazer; não tem tempo nem equipe para cruzar planilha |
| Objetivos | Saber onde está o dinheiro, por que mudou, e quanto comprar no mês que vem — em minutos, sem montar planilha e sem contratar ninguém |
| Cenário de uso | Fim do mês: exporta o relatório do ERP, sobe no sistema e vê o CMV, os itens que mais pesam e a sugestão de compra do mês seguinte. Decide a compra na mesma sessão |
| Frase-chave | _(hipótese — esta persona **não foi entrevistada**; ela é derivada da dor validada nas Personas 1 e 2, removendo a estrutura de escritório. Validá-la é o primeiro passo de qualquer continuação do projeto)_ |

> ⚠️ Mantida por registro, não como alvo. Para atendê-la, o produto teria que
> **criar** o dado (ficha técnica, contagem de estoque) antes de analisá-lo — é
> outro produto (mini-ERP), fora de escopo.
>
> A Persona 3 é a única sem evidência de entrevista atrás. Isso está dito aqui
> de propósito: o documento proíbe requisito sem evidência, e inventar uma frase
> de cliente para ela seria pior que admitir a lacuna.

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
| RF06 | Geração automática de DRE consolidada entre casas | **Won't** | **Fora de escopo desde 06/11** — sem dado das outras casas | Persona 2 |
| RF07 | Recomendação de quantidade de compra a partir do histórico de vendas | **Must** | **Entregue 06/11** — endpoint + tela "Quanto comprar" | Persona 1 / Persona 2 (era Persona 3 até 07/11) |
| RF09 | Anexo de nota fiscal fotografada ao custo do período | **Should** (era Must) | **Fora do ciclo 07–09/11** — especificado em `10-anexos-de-imagem.md` | Persona 1 |
| **RF11** | **Explicação do ajuste**: contribuição por grupo, subgrupos comparáveis, resumo em linguagem simples e até 2 sugestões, por regras | **Must** | **Entregue 07/11** — campo `explicacao` no fechamento + tela (`11-ciclo-explicacao-do-ajuste.md` §3) | Persona 2 (lê) / Persona 1 (confere) |
| **RF12** | Fluxo guiado "Fechar o mês" (unidade → teórico → real → resultado) com planilha-modelo | Should | **Entregue 07/11** — aba "Fechar o mês" (§5); não precisou do corte | Persona 1 |
| **RF13** | Tempo medido do primeiro envio ao resultado | Should | **Entregue 07/11** (§6) | Persona 2 |
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
Persona: desde 07/11/2026, Personas 1 e 2 — a fala de origem ("você parte do
senso do chefe") é da Conversa 1, do caso Saints. O texto abaixo sobre a
Persona 3 é o motivo histórico da subida para Must.
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

RF11 — Explicação do ajuste teórico × real
Prioridade: Must
Descrição: Para todo fechamento com os dois lados, o sistema diz onde está a
diferença e o que conferir: contribuição de cada grupo ao ajuste total, em R$ e
em pontos do total; subgrupos comparados quando existem com o mesmo nome nos
dois lados; situação em três ramos (acima / dentro / abaixo do previsto, limiar
de ±1 pp declarado como premissa); um parágrafo em linguagem simples para o
sócio e até 2 sugestões de conferência. Tudo por regras, sem LLM.
Origem: Conversa 1 — "eu preciso abrir o relatório da Joyce, [...] o de
compras, [...] a perda e tentar achar a ligação dos dois". Revisão de 07/11: o
ERP já tem os números; o que falta é a ligação.
⚠️ Limites declarados na própria resposta: abaixo do grupo, o dado só permite
comparar subgrupos que existem nos dois relatórios (cardápio agrupa por venda,
compras por insumo). Ajuste abaixo do previsto não é tratado como economia.
Especificação, contrato e testes: `11-ciclo-explicacao-do-ajuste.md` §3.

RF12 — Fluxo guiado "Fechar o mês"
Prioridade: Should
Descrição: Uma aba nova conduz unidade e período → lado teórico → lado real →
resultado, mostrando em cada passo as colunas exigidas e um botão para baixar a
planilha-modelo. Não substitui as abas atuais. Upload já existente é reutilizado
por padrão; substituir exige confirmação.
Origem: o contrato de entrada (`07-fechamento-cmv.md`) só ajuda se aparecer
na hora do envio.
Especificação: `11-ciclo-explicacao-do-ajuste.md` §5.

RF13 — Tempo do primeiro envio ao resultado
Prioridade: Should
Descrição: O frontend mede o tempo de relógio do primeiro envio até o resultado
aparecer e o exibe, com a ressalva de que não inclui exportar do ERP.
Origem: a métrica "de ~2 dias para < 5 min" (1.6) nunca foi medida.
⚠️ Os ~2 dias são declarados pelo cliente; a comparação é de ordem de grandeza.
Especificação: `11-ciclo-explicacao-do-ajuste.md` §6.
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
US11 — relacionada a RF11

Como sócio de uma rede de bares (Persona 2),
quero ler no topo do fechamento onde ficou a diferença entre o custo real e o
previsto e o que conferir,
para decidir o que cobrar da operação sem depender de interpretar a planilha.

Critérios de aceitação:
  DADO um fechamento com os dois lados e ajuste total acima de +1 pp
  QUANDO consulto GET /api/v1/metricas/fechamento
  ENTÃO explicacao.situacao = "acima", o resumo cita o grupo que mais
        contribuiu e há no máximo 2 sugestões

  DADO um fechamento com ajuste total abaixo de −1 pp
  QUANDO consulto o fechamento
  ENTÃO explicacao.situacao = "abaixo" e o resumo não apresenta a diferença
        como economia

  DADO um fechamento com ajuste entre −1 e +1 pp
  QUANDO consulto o fechamento
  ENTÃO explicacao.situacao = "dentro" e não há sugestões

  DADO um fechamento com dois grupos
  QUANDO somo contribuicao_pp de todos os grupos
  ENTÃO o resultado é igual a total.ajuste_pp (± 0,02)

  DADO um período com só um dos lados enviado
  QUANDO consulto o fechamento
  ENTÃO a resposta é 200 com explicacao = null

US12 — relacionada a RF12

Como analista de custos (Persona 1),
quero fechar o mês num fluxo único que me diz o que cada arquivo precisa ter,
para não errar o envio e não ter que lembrar a ordem das telas.

Critérios de aceitação:
  DADO que estou no passo do lado teórico
  QUANDO clico em "Baixar planilha-modelo"
  ENTÃO recebo um .xlsx que, reenviado sem mudanças, é aceito com 201

  DADO que já existe upload daquele lado e período
  QUANDO chego ao passo
  ENTÃO o padrão é reutilizar o upload existente, e substituir exige confirmação

  DADO que envio um arquivo sem a coluna "custo"
  QUANDO o passo processa o envio
  ENTÃO vejo a mensagem do 422 em português dizendo qual coluna falta

US13 — relacionada a RF13

Como sócio (Persona 2),
quero ver quanto tempo o sistema levou do primeiro envio ao resultado,
para comparar com os dias que o fechamento leva hoje.

Critérios de aceitação:
  DADO que concluí os envios do mês
  QUANDO o resultado aparece
  ENTÃO vejo "Do primeiro envio ao resultado: X s" e a ressalva de que não
        inclui exportar do ERP
```

> INVEST: Independent, Negotiable, Valuable, Estimable, **Small (1–3 dias)**, Testable.
> 2 a 5 critérios GWT por story — eles viram os testes em `tests/`.

---

## 7. Priorização (MoSCoW)

Repriorizado em 07/11/2026, na volta às Personas 1 e 2. O que mudou e por quê
está na primeira linha do histórico.

| Nível | Requisitos | Estado |
|---|---|---|
| **Must** — o MVP | RF08 (CRUD de unidade) · RF01 (upload do export) · RF02 (CMV teórico × real) · RF04 (dashboard) · RF07 (recomendação de compra) · **RF11 (explicação do ajuste)** | **Todos no ar**, com tela |
| **Should** | **RF12 (fluxo guiado)** · **RF13 (tempo medido)** · RF09 (anexo de nota fiscal) · RNF03 autenticação · registro de perda com foto · decomposição do ajuste em contagem + perdas + não explicado · **tratamento da deriva de nome de item** (ver 1.9) | RF12/RF13 entregues em 07/11 e no ar; demais não entregues |
| **Could** | Alerta de variação de custo unitário por item · curva ABC de concentração de custo · OCR de nota fiscal | Nenhum iniciado |
| **Won't** (documentado) | RF03 (funcionários) · RF05 (alerta de escala) · **RF06 (DRE consolidada entre casas)** · integração via API do Everest | Fora de escopo, com motivo |

**Por que RF11 entra como Must:** o ERP do cliente já tem os números; mostrar o
ajuste formatado agrega pouco. O valor está em dizer onde está a diferença e o
que conferir. Sem RF11, o produto é um relatório mais rápido; com ele, encurta o
diagnóstico.

**Por que RF09 desceu para Should:** tinha subido para Must em 06/11 como aposta
ligada à Persona 3 e ao uso do Blob para imagem. Com a volta às Personas 1 e 2,
a nota fiscal como prova continua útil à analista, mas não é o que explica o
ajuste — e não cabe no ciclo de 07–09/11.

**Por que RF06 segue Won't:** com a volta da Persona 2, a DRE consolidada
recupera sentido, mas só há dado real de **uma** casa. Consolidar uma casa não
prova nada.

**Por que RF03 e RF05 seguem Won't:** nunca saíram de hipótese. Dependiam de uma
Conversa 3 que não aconteceu e, no caso de RF03, de o RH definir quais dados
pessoais entram (LGPD). Sem cliente respondendo, construir seria adivinhar.

**Por que a integração com a API do Everest é Won't:** ela amarraria o produto a
um fornecedor de ERP. A planilha genérica é o caminho para qualquer origem — e é
justamente o que sustenta a tese de generalização (1.8). E o cliente, que
precisaria liberar o acesso, parou de responder.

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
| 10/11/2026 | 1.4 | **O lado real da casa piloto deixa de ser chamado de CMV real.** A DRE do Everest é compras do mês; o CMV real é compras + estoque inicial − estoque final. Cada upload do lado real ganha `base_real` (`compras` \| `consumo` \| `declarada`); a planilha genérica aceita `estoque_inicial`, `compras`, `estoque_final` e calcula o custo. O fechamento ganha `acumulado` (12 meses, conclusivo a partir de 6 com base compras). O leitor da DRE aceita o layout sem código de conta (abas `ENTRADA` da planilha da equipe) e `scripts/importar_dre_historica.py` importa jun–dez/22. Campos novos opcionais; `ajuste_pp` de set/26 continua −3,68 (mudou a leitura, não o número). Ainda **não publicado** | A planilha de fechamento da equipe (recebida em 23/10, analisada em 10/11) mostra a variação de estoque somada à parte da DRE. O −3,68 pp de set/26 estava sendo apresentado como desvio, mas está dentro da oscilação normal de compras × teórico de um mês (−7,2 a +9,3 pp em jun–dez/22). O time confirmou que não há inventário disponível, então a leitura possível é o acumulado |
| 07/11/2026 | 1.3 | **RF11, RF12 e RF13 entregues e publicados** — backend e frontend no commit `a7fa9c5`, conferidos em produção: `/health` com o SHA novo e o fechamento de set/26 com `ajuste_pp: -3.68` e `explicacao.situacao: "abaixo"`. Roteiro de demo (`08`) reescrito com o que está no ar. Limitação nova em 1.9: nomes que diferem só no singular/plural não são comparados | Conclusão do ciclo 07–09/11. A limitação nova não é regressão: apareceu porque o RF11 passou a comparar abaixo do grupo e, com isso, tornou visível uma diferença de cadastro que antes ninguém via |
| 07/11/2026 | 1.2 | **RF11, RF12 e RF13 implementados** (branch do ciclo, ainda não publicado): `explicacao` no fechamento com as três situações, contribuição por grupo, grupos e subgrupos sem par; aba "Fechar o mês"; tempo do primeiro envio ao resultado. **P0 entregue**: tradutores padronizam nome de grupo e subgrupo, e `GET /api/v1/modelos/{tipo}` gera a planilha-modelo. A limitação de maiúsculas em 1.9 sai da lista. Nada marcado como "entregue" ainda: pela regra do ciclo isso só vale depois do deploy conferido no `/health` | Execução do ciclo 07–09/11 na ordem da seção 2 de `11-ciclo-explicacao-do-ajuste.md`. Nenhum item precisou do corte previsto. O roteiro de demo (`08`) segue descrevendo só o que está no ar, e é atualizado junto com o deploy |
| 07/11/2026 | 1.1 | **Voltam as Personas 1 e 2** (analista alimenta, sócio decide); Persona 3 vira hipótese de mercado futuro. **RF11** (explicação do ajuste, Must), **RF12** (fluxo guiado, Should) e **RF13** (tempo medido, Should) especificados em `11-ciclo-explicacao-do-ajuste.md`. **RF09 desce para Should.** Problema (1.1) e objetivo (1.4) reescritos: o valor é explicar o ajuste, não mostrá-lo. Contrato de entrada ("o que o usuário precisa fornecer") em `07-fechamento-cmv.md`. Três limitações novas em 1.9 | Revisão crítica (Lean Inception): o app mostrava o delta sem explicá-lo, e o ERP do cliente já tem o número. A Persona 3 tinha sido criada para generalizar a solução, mas generalizar o **formato** não exige mudar de **público** — e ela não tinha entrevista nem os dados que o cálculo exige (ficha técnica e inventário). As DEMO continuam, com o papel declarado: sem os dados das outras casas do Saints para a apresentação, provam formato e regra, não mercado |
| | 0.1 | Criação | Estrutura inicial |
| 13/09/2026 | 0.2 | Preenchidas Personas (seção 3), RF01–RF07 e RNF01–RNF06 | Baseado na Conversa 1 (`00-customer-discovery.md`) e na pesquisa técnica de Everest/Colibri/Dionísio (`docs/discovery/`). RF03, RF05 e RF06 marcados como hipótese de solução — pendente validação de fluxo operacional com Joyce, Renata e Wellington (Conversa 2, ainda não realizada) |
| 17/09/2026 | 0.2 | Corrigido nome do cliente de "Grupo Santos" para **Grupo Saints** em todos os docs; nomes das casas atualizados com base no site institucional ([gruposaints.com.br](https://www.gruposaints.com.br/)) | O nome "Grupo Santos" era erro de transcrição automática do áudio da entrevista (confirmado ao ouvir a resposta do cliente na transcrição, `Entrevista/entrevista_cliente.txt` linha 192); site oficial confirma "Grupo Saints" e lista as marcas: Boteco São Bento, Tartuferia San Paolo, Casa Yū, Tuy Bar Cocina, São Conrado Bar, Toca do Urso, Beer Island Tap House. "Tulipa", citado na entrevista, não aparece no site — sinalizado como pendente de confirmação |
| 09/10/2026 | 0.3 | Adicionado **RF08** (CRUD de Casa); preenchida coluna Sprint — RF08/RF01/RF02 → Sprint 1, RF04 → Sprint 2, RF06 → Sprint 2 (se sobrar tempo), RF03/RF05 → adiados, RF07 → fora do MVP atual | Retomada do projeto após período sem desenvolvimento de domínio (código ainda tinha só o placeholder `Item`). Conversa 2 (Joyce/Renata/Wellington) ainda não aconteceu; decisão foi priorizar o Problema 1 (custo/compras), já validado na Conversa 1, para não bloquear a Sprint 1 esperando a entrevista. RF08 nasceu da necessidade de uma entidade "casa" que todo RF Must já referenciava implicitamente |
| 03/11/2026 | 0.4 | RF01 passa a aceitar os **exports reais do Everest** em .xlsx, em dois tipos (`cardapio` = CMV teórico, `compras` = CMV real); RF02/RF04 passam a ser o **fechamento de CMV** (teórico × real × ajuste por grupo, evolução mensal, top itens). Detalhes em `07-fechamento-cmv.md` | Conversa 2 (Marcela, operação/custos) e análise dos exports reais: teórico e real vêm de relatórios separados (não existe o CSV com as duas colunas que o RF01 supunha), o CMV real já é pós-inventário, e a dor validada diretamente é o relatório de fechamento manual (~2 dias por casa). MVP focado numa casa piloto (Boteco São Bento - Vila Madalena) |
| 05/11/2026 | 0.5 | **RF04 entregue**: frontend React (Casas, Upload, Fechamento) publicado no Static Web Apps, consumindo a API de fechamento em produção. RF01/RF02/RF08 confirmados rodando ponta a ponta em produção (Azure SQL + Blob Storage) | Fechamento do MVP Must para a apresentação de 09/11. Falta só o CMV de compras real de jul–set/26 (pedido à Marcela em 03/11) para a demo com dado real completo |
| 06/11/2026 | 1.0 | Documento sincronizado com o que está efetivamente em produção: quatro unidades de demonstração carregadas (1.8), RF07 com tela além do endpoint, `/health` informando o SHA publicado, e a observabilidade registrada como lacuna em 1.9 ao lado da autenticação | Fechamento da entrega. A versão anterior descrevia intenção em alguns pontos e produção em outros; agora cada afirmação foi conferida contra o ambiente no ar — inclusive que o dado real do cliente seguiu intacto depois da carga de dado fictício |
| 06/11/2026 | 0.9 | **RF09 sobe para Must** (aposta de produto declarada, não requisito validado). **RF10 retirado** no mesmo dia em que foi criado: a foto não fazia o trabalho de identidade — o mapeamento de aliases fazia — e o recurso obrigaria a manter dois caminhos de agregação para sempre, para não quebrar números já conferidos contra produção. O problema que ele atacava (deriva de nome de item) virou **risco registrado em 1.9**, desacoplado de qualquer funcionalidade de foto | Com o prazo curto e sem cliente respondendo, a estratégia passou a priorizar flexibilidade: esperar validação é paralisia, então RF09 é apostado de propósito e isso está dito em vez de disfarçado. A retirada do RF10 veio de uma pergunta do próprio grupo — "por que a foto como âncora de identidade, isso não dificulta outras funcionalidades?" — e a resposta era sim: dificultava |
| 06/11/2026 | 0.8 | Adicionados **RF09** (anexo de nota fiscal fotografada) e **RF10** (cadastro de produto com foto como âncora de identidade), os dois como **Should** e **especificados sem implementar** em `10-anexos-de-imagem.md`. Criada a auditoria `09-uso-da-nuvem.md`, com a fila de ajustes de nuvem ordenada por valor. Seção 8 (extras valorizados) passa a registrar **recusa com motivo** de Redis e API Management | Decisão de priorizar funcionalidades que justifiquem o Blob Storage com **imagem**, em vez de aprofundar estatística no RF07 — o projeto é de conceito de nuvem, e Blob guardando só planilha subaproveita o recurso. A auditoria da configuração real achou quatro distâncias entre o que este documento afirmava e o que estava no ar, a pior delas sendo **nenhum log habilitado** apesar da regra 9. RF09 e RF10 entram como Should, não Must, porque nenhuma das duas foi validada com usuário e a Persona 3 segue não entrevistada |
| 06/11/2026 | 0.7 | **Reposicionamento para pequeno negócio.** Nova **Persona 3** (dono de pequeno negócio) como alvo do produto, com as Personas 1 e 2 rebaixadas a caso de origem. **RF07 sobe de Could para Must e é entregue** (`/api/v1/metricas/recomendacao-compra`). **RF06 vira Won't.** Seção 7 (MoSCoW), que estava vazia desde a criação do documento, preenchida com motivo para cada Won't. Nova limitação registrada em 1.9: set/26 é o mês mais fraco da série | Sem PO ativo, manter como alvo um grupo de 14 casas com escritório central era descrever um cliente que não existe mais para o projeto. O alvo passou a ser quem tem a mesma dor **sem** a estrutura: a Joyce gasta 5 dias por mês montando planilha, o dono da padaria não tem Joyce. Isso reordenou a prioridade — RF06 (DRE de 14 casas) deixou de fazer sentido e RF07 ("quanto comprar", que o cliente decide "pelo senso") virou o requisito que transforma o produto de relatório em apoio à decisão. A Persona 3 é declaradamente **não entrevistada**, e validá-la é o primeiro passo de qualquer continuação |
| 06/11/2026 | 0.6 | Cliente passa a **caso de estudo** (1.7); adicionadas a **tese de generalização** (1.8) e as **limitações conhecidas** (1.9), incluindo a proveniência não provada da DRE; registrado o ambiente em produção no topo | O Grupo Saints não respondeu ao pedido de 03/11 nem à Conversa 3, então o projeto não pode mais ser validado por um PO ativo — o que sobra como prova é a base real que ele já cedeu. Isso deslocou a pergunta de "o cliente aprovou?" para "isto serve a outro negócio?", e a resposta exigiu tirar do código o que era específico de restaurante: a lista `("ALIMENTOS", "BEBIDAS")` virou dedução a partir do dado, e um terceiro tradutor passou a aceitar planilha de qualquer ERP. A base real continua dando exatamente os mesmos números depois da mudança |
