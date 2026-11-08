# Roteiro da demonstração — 100% na nuvem

> Criado em 06/11/2026, depois de uma apresentação em que o projeto foi mostrado
> clonando o repositório numa máquina da faculdade e dependendo de `uv`, Node,
> driver ODBC e `.env` para rodar. **Nada disso é necessário.** A aplicação está
> em produção; a demonstração é um navegador e cinco links.

> **Ciclo 07–09/11 entregue e publicado em 07/11.** Explicação do ajuste
> (RF11), fluxo guiado "Fechar o mês" (RF12) e tempo medido (RF13) estão **no
> ar** — backend no commit `a7fa9c5`, frontend no mesmo deploy, os dois
> conferidos. Este roteiro já descreve isso. A especificação de cada item está
> em `11-ciclo-explicacao-do-ajuste.md`.

## Regra número um

**Não instale nada, não clone nada, não abra terminal.** Se a demonstração
precisa de um comando para começar, ela já falhou — o avaliador vai ver você
resolvendo ambiente em vez de ver o produto.

Terminal só aparece em um momento opcional, no fim (passo 7), e para provar
CI/CD, não para rodar a aplicação.

## Antes de sair de casa

| # | Verificação | Como |
|---|---|---|
| 1 | A API está acordada | Abra https://app-projeto4-saints2026.azurewebsites.net/health — tem que responder `{"status":"ok", ..., "banco":"ok"}` **na hora** |
| 2 | É o código mais recente | No mesmo `/health`, confira que `commit` bate com o último commit da `main` (`git rev-parse HEAD`) |
| 3 | O frontend carrega, com 5 abas | Abra https://zealous-river-0b6019910.6.azurestaticapps.net — Casas, Upload, **Fechar o mês**, Fechamento e Quanto comprar |
| 4 | As 5 unidades estão lá | Aba Casas: a piloto real + 4 de demonstração, com "(DEMO)" no nome |
| 5 | O fechamento calcula | Abra [o fechamento de set/26](https://app-projeto4-saints2026.azurewebsites.net/api/v1/metricas/fechamento?casa_id=2&periodo=2026-09) e confirme `ajuste_pp: -3.68` |
| 6 | **A explicação vem junto** | No mesmo JSON, o campo `explicacao` tem que existir, com `"situacao":"abaixo"`. Se vier `null` ou faltar, o backend no ar é anterior ao ciclo 07/11 |
| 7 | Há crédito no Azure | Portal → Cost Management. Se o crédito acabar, tudo cai |

Deixe as abas **já abertas** na ordem do roteiro, numa janela só. Trocar de aba
na frente de alguém é melhor que digitar URL.

> **Se o passo 1 demorar 30–60 segundos**, o Always On caiu. Ele foi **ligado
> em 06/11/2026** justamente porque a instância dormia em ~20 min e a primeira
> requisição levava um minuto — era o que fazia a aplicação parecer quebrada.
> Confira com
> `az webapp config show -g rg-projeto4 -n app-projeto4-saints2026 --query alwaysOn`.
>
> **Se o passo 2 mostrar um commit diferente**, o deploy publicou mas o processo
> não trocou: `az webapp restart -g rg-projeto4 -n app-projeto4-saints2026`.

---

## O roteiro (18–22 min)

### 1. O problema, antes de qualquer tela (2 min)

Não comece pelo sistema. Comece pela planilha.

> "Toda casa do grupo fecha o CMV do mês à mão. A equipe exporta três módulos
> do ERP, cola em planilha e cruza. Leva cerca de **dois dias por casa, por
> mês**, e o resultado só sai perto do dia 15 — quando o prejuízo já aconteceu.
> O cliente descreveu assim: *'você clica lá exportar, aí vem um Excel cru, sem
> formatação, sem nada'*."

Se puder, mostre um export real aberto no Excel por 10 segundos. É a imagem mais
convincente da apresentação: um relatório de impressão, com cabeçalho de
empresa, totais no meio dos itens e hierarquia por indentação.

### 2. A aplicação, pelo caminho do usuário (4 min)

https://zealous-river-0b6019910.6.azurestaticapps.net

Cinco abas, na ordem do fluxo real: **Casas → Upload → Fechar o mês →
Fechamento → Quanto comprar**.

- **Casas** → o CRUD do RF08. Mostre a casa piloto, o Boteco São Bento - Vila Madalena, e diga que as outras quatro são de demonstração (o nome carrega "(DEMO)").
- **Fechamento** → escolha a casa piloto, período **09/2026**, Calcular.

**Quem é quem.** A analista de custos sobe os relatórios; o sócio lê o
resultado e decide. O sistema é para os dois — não para "qualquer pequeno
negócio" (ver a pergunta sobre isso no fim).

**Leia o parágrafo da tela em voz alta, antes de falar do número.** Ele é o
item que mudou o produto neste ciclo, e aparece acima do indicador de propósito:

> "Em 2026-09, o CMV (custo das mercadorias vendidas) real ficou 3,68 pontos
> abaixo do previsto pelas fichas técnicas (R$ … a menos). Diferença nesse
> sentido costuma apontar algo faltando no lado real — compra não lançada,
> inventário de fim de mês superestimado — ou sobrando no teórico. A maior
> parte veio de BEBIDAS (−2,30 pp)."

Logo abaixo, em **"O que conferir"**, duas ações: checar se todas as compras de
BEBIDAS foram lançadas e se o inventário não está superestimado; e confirmar
que os dois relatórios são do mesmo período.

> "O ERP do cliente já mostra esse número. O que ele não diz é **onde
> procurar**. É isso que o sistema passou a fazer."

Só então pare no indicador e deixe ele respirar:

| | |
|---|---|
| CMV teórico | **25,54%** |
| CMV real | **21,86%** |
| **Ajuste** | **−3,68 pp** · selo **"Abaixo do previsto"**, em âmbar |

Os valores em R$ aparecem na tela, ao vivo — e é com eles que o número
convence. Eles **não** estão escritos aqui de propósito: este repositório é
público e faturamento de uma unidade identificada do cliente não vai para o
Git. Leia na tela, não no roteiro.

**O sinal é o ponto mais importante da demonstração.** O ajuste é **negativo**:
o real ficou **abaixo** do teórico. Isso **não é economia** — e a tela diz isso
com todas as letras. Até 07/11 ela marcava esse mesmo mês como "Favorável", em
verde, o que era simplesmente falso; agora são três estados (acima / dentro /
abaixo) e "abaixo" é âmbar de atenção, não verde de parabéns.

> "Ajuste grande, para qualquer lado, quer dizer 'tem erro em algum lugar' —
> ficha técnica errada, contagem errada, perda não lançada, desvio. O sistema
> aponta onde olhar; quem conclui é a equipe de custos."

Se perguntarem de onde vem o "±1 ponto": está escrito na própria tela que é
**premissa nossa, não parâmetro do cliente**. O gabarito de fechamento da
equipe nunca chegou.

- Role até a tabela de grupos → a coluna **Contribuição** é a que soma ao ajuste do mês. A coluna "Ajuste (pp)" de cada grupo usa a venda do próprio grupo e **não** soma: BEBIDAS aparece com −4,23 pp de ajuste e −2,30 pp de contribuição, e os −2,30 e −1,37 é que fecham os −3,68.
- Role até **Abaixo do grupo** → quatro categorias comparadas, **todas em BEBIDAS**. Em ALIMENTOS não há nenhuma, e a tela explica por quê (ver passo 2b).
- Role até **Evolução mensal** → 24 meses de CMV teórico, de set/24 a set/26.
- Role até **Top itens** → onde o custo está concentrado.

### 2b. O limite do dado, dito pela própria tela (1 min)

Ainda em Fechamento, no bloco **Abaixo do grupo**, está a tarja:

> "O ERP informa compras por categoria de insumo e vendas por categoria de
> cardápio. Abaixo do grupo, só comparamos as categorias que existem com o
> mesmo nome nos dois relatórios."

E embaixo, **"Composição do custo — categorias que existem em um lado só. Não
são desvio."**, com mais de trinta linhas: PETISCOS e PRATOS A LA CARTE do lado
teórico, BOVINOS e HORTIFRUTI do lado real.

É o melhor momento do roteiro para a tese de honestidade do trabalho:

> "Em BEBIDAS os dois relatórios usam os mesmos nomes — CHOPP é CHOPP dos dois
> lados —, então comparamos. Em ALIMENTOS não dá: o cardápio agrupa por como se
> vende (PETISCOS) e a compra por insumo (BOVINOS). Sem a ficha técnica
> explodida em insumos, cruzar os dois seria inventar um número. O sistema
> prefere declarar o limite a preencher a tabela."

Se trocar para uma casa **(DEMO)**, a mesma seção fica cheia e sem tarja: lá os
subgrupos coincidem nos dois lados. Vale apontar a diferença em vez de deixar
alguém notar sozinho — é a prova de que a comparação segue o dado, não a tela.

### 2c. Fechar o mês, do zero ao resultado (2 min)

Aba **Fechar o mês** (RF12). Quatro passos: casa e período → lado teórico →
lado real → resultado.

**Use uma casa (DEMO) ou um período novo. Nunca a casa piloto em 09/2026** —
reenviar substitui o dado real, ao vivo.

- Em cada passo de envio aparece **a tabela de colunas daquele lado** e o botão **Baixar planilha-modelo**, que a API gera na hora. Não existe `.xlsx` versionado no repositório: dado de cliente não entra no Git, então o modelo é gerado, não guardado.
- Quando já existe arquivo do período, o padrão é **"Usar o já enviado"**. Substituir exige um segundo clique e vem com aviso de que não dá para desfazer.
- No fim: **"Do primeiro envio ao resultado: X s"** (RF13), com a ressalva colada — *não inclui o tempo de exportar os relatórios do ERP*.

> "Os dois dias do processo manual são o que a equipe de custos **declarou**, e
> incluem exportar do ERP. Os segundos aqui são outra coisa. A gente mede o que
> mede e diz o que não mede."

Esta aba existe porque o erro mais caro do contrato de entrada é silencioso:
quem manda só o cardápio vê um painel que parece completo e não tem ajuste
nenhum. A aba **Upload** continua lá, inalterada, para quem já sabe o que
precisa enviar.

### 3. O upload, ao vivo (2 min)

Vá em **Upload**, escolha a casa, o período e o tipo, e envie um `.xlsx`.

Mostre que o sistema avisa quando já existe upload daquele período e tipo, e que
reenviar **substitui** — é o fluxo real: o mês fecha, chega correção, reenvia.

Se o arquivo não for reconhecido, a resposta é **422 com mensagem em português
dizendo qual coluna falta** — não um stack trace. Vale mostrar de propósito.

### 4. Por que isto serve a outro negócio (3 min)

É o ponto que diferencia o trabalho, e precisa ser dito com cuidado.

> "O cliente parou de responder depois da segunda conversa. Em vez de inventar
> uma validação que não houve, usamos a base real dele para provar uma
> afirmação verificável: **o cálculo não depende do ERP dele nem do ramo dele.**"

**Diga a fronteira junto com a tese:** *"Funciona para qualquer
operação que tenha ficha técnica e inventário mensal e exporte uma tabela com
grupo, custo e venda. Provamos com um ERP real e quatro ramos sintéticos."* O que
o usuário precisa fornecer está em `07-fechamento-cmv.md` — se perguntarem, é
para lá que se aponta.

Ainda em **Fechamento**, troque a casa — são **quatro ramos diferentes**, e o
seletor é a demonstração inteira. Não precisa mostrar os quatro: mostre dois
bem distantes e mencione os outros.

| Unidade | CMV teórico | CMV real | Grupos que o sistema **deduziu** |
|---|---|---|---|
| Drogaria Central (DEMO) | 47,79% | 52,09% | MEDICAMENTOS, PERFUMARIA |
| Padaria Sao Jose (DEMO) | 38,45% | 41,91% | CONFEITARIA, FRIOS, PANIFICACAO |
| Pizzaria Bella (DEMO) | 32,39% | 35,30% | BEBIDAS, PIZZAS, SOBREMESAS |
| Distribuidora Horizonte (DEMO) | 75,94% | 82,78% | CERVEJAS, DESTILADOS, NAO ALCOOLICOS |

O par mais convincente é **Pizzaria (32%) × Distribuidora (76%)**: margem de
restaurante contra margem de atacado, no mesmo cálculo, sem nenhuma
configuração.

Três coisas para dizer enquanto troca o seletor:

- **Nenhuma linha de código conhece essas categorias.** Elas são deduzidas: comparável é o grupo que os dois lados do fechamento reportam.
- O dado entrou por **planilha genérica**, não por relatório do Everest.
- Em cada ramo há um grupo de custo indireto que o sistema **excluiu sozinho** — EMBALAGENS na farmácia, MATERIAL DE LIMPEZA na padaria, DESCARTAVEIS na pizzaria, LOGISTICA na distribuidora. É o mesmo mecanismo que exclui UTENSILIOS da DRE do restaurante.

Diga que o dado é fictício **antes** de alguém perguntar. O nome carrega
"(DEMO)" exatamente para isso — e o fechamento da casa piloto real continua
intacto ao lado, o que foi conferido de propósito.

Se o avaliador abrir o código, o argumento se sustenta em dois lugares:

| Arquivo | O que mostrar |
|---|---|
| `app/services/leitores.py` | Três tradutores, uma `LinhaCusto` só. Adaptar a um ERP novo = escrever um tradutor |
| `app/crud.py`, `grupos_comparaveis` | Antes era `GRUPOS_CMV = ("ALIMENTOS", "BEBIDAS")` cravado. Agora é deduzido: comparável é o grupo que os **dois** lados reportam — e na base real devolve exatamente ALIMENTOS e BEBIDAS |

### 4b. Quanto comprar — o passo que sai do relatório (2 min)

Aba **Quanto comprar**. Mesma casa, período **09/2026**, Calcular.

É o ponto em que o sistema deixa de descrever o passado. O cliente decidia
compra "pelo senso do chefe" — essa é a fala que originou o RF07.

O que mostrar, e nesta ordem, porque a ordem é o argumento:

1. **A tarja vermelha no topo.** O sistema avisa que o próprio dado de entrada é suspeito: *"o volume vendido em 2026-09 foi 39% abaixo da mediana dos outros meses, em todos os itens ao mesmo tempo"*. Queda uniforme em todo o catálogo quase nunca é mercado — costuma ser relatório incompleto. **O sistema não corrige, avisa.**
2. **O bloco de método**, que diz literalmente "não é machine learning". É média móvel com tendência e sazonalidade, auditável de propósito: quem decide compra tem o direito de conferir o número.
3. **O aviso de estoque zero.** A sugestão é um **teto**, não uma ordem de compra — o sistema lê relatórios, nunca uma contagem, então não sabe o que está na prateleira.
4. **A coluna "Efeito do mês".** Procure uma linha onde a sugestão é bem maior que a média: é sazonalidade, e a coluna mostra quanto. Sem ela a tabela ficaria inexplicável justamente onde alguém desconfiaria.
5. **O selo de confiança**, com o motivo ao passar o mouse: *"24 meses, mas a venda oscila muito (variação 41%)"*.

> Se perguntarem "por que não um modelo de machine learning?": porque com 24
> meses de histórico mensal e no máximo duas observações por mês do ano, um
> modelo treinado não teria dado para aprender nada além disto — e teria a
> desvantagem de ninguém poder auditar o número que orienta a compra.

### 5. A arquitetura (2 min)

https://app-projeto4-saints2026.azurewebsites.net/docs

O Swagger vale mais que um diagrama: é o contrato, gerado do código. Mostre
`/health` respondendo e comente o que ele significa — é o que o App Service usa
para decidir reiniciar a instância.

```
Static Web App (React)  ──▶  App Service (FastAPI)  ──▶  Azure SQL
         CDN + TLS                gunicorn/uvicorn          dado estruturado
                                        │
                                        └──────────────▶  Blob Storage
                                                          arquivo original
```

Dois pontos que rendem pergunta, com a resposta pronta:

- **Por que o arquivo não vai para o banco?** Binário em banco relacional é caro e não escala. Padrão cloud: binário no object storage, ponteiro no banco.
- **Por que o nome do blob é um UUID?** Nome de arquivo enviado pelo cliente nunca vira nome de blob — é vetor de path traversal e de colisão.

### 6. O que não está pronto (1 min)

Diga antes de ser perguntado. É o que separa um trabalho honesto de um
demonstrado só até onde funciona.

- **A API é pública.** Autenticação era RNF03 da Sprint 2 e não foi entregue. É a lacuna mais séria do trabalho.
- **Sem Application Insights.** Os logs do App Service foram ligados em 06/11 (antes disso nem existiam), mas observabilidade de verdade — requisição, latência, falha ao longo do tempo — ficou como nível 2 da fila em `docs/09-uso-da-nuvem.md`.
- **RF09 (nota fiscal fotografada) está especificado e não construído**, em `docs/10-anexos-de-imagem.md`. Desceu para Should em 07/11.
- **O sistema encurta o diagnóstico, não previne.** O CMV real depende do inventário do dia 30. Delta semanal e alertas são roadmap.
- **A DRE real não diz de qual casa nem de qual mês é.** O rótulo set/26 foi atribuído por nós, com base em evidência circunstancial. É a limitação mais importante do trabalho e está escrita em `docs/01-requisitos.md` 1.9.
- **Um mês de CMV real.** 24 meses de teórico, 1 de real: a série de ajuste tem um ponto.
- **Uma casa real.** O consolidado entre casas é exercitado com a unidade de demonstração.

### 7. CI/CD (opcional, 2 min)

Só se houver tempo e interesse. É aqui que o terminal pode aparecer.

- Aba **Actions** do repositório → `deploy-azure.yml` verde.
- O deploy **não roda sem os testes passarem** (`needs: [testes]`).
- Autenticação por **OIDC**: nenhum segredo de longa duração guardado no GitHub.
- **A verificação compara o SHA publicado com o que o `/health` informa.** Abra o log do último deploy: aparecem várias tentativas com `"status":"ok"` **antes** de o commit certo entrar no ar. Uma verificação que olhasse só o status daria sucesso na primeira — e deu, em 06/11/2026, com o código anterior rodando. Health check genérico prova que a aplicação está de pé, não que está de pé com o código que subiu.

> Se sobrar interesse, esta é a melhor história de engenharia do trabalho:
> auditando a própria configuração, descobrimos que **o deploy automático nunca
> havia funcionado** (subject OIDC com nome em vez de ID) e que a verificação
> pós-deploy era decorativa. As duas estão corrigidas e documentadas em
> `docs/06-guia-deploy-azure.md`, Atenção 4b e 6.

---

## Perguntas que provavelmente vêm

| Pergunta | Resposta curta |
|---|---|
| "Esse ajuste de −3,68 pp é economia?" | Não. É divergência entre o que deveria ter custado e o que custou. Para qualquer lado, significa "tem erro em algum lugar" |
| "Como vocês sabem que a DRE é de setembro?" | Não sabemos com certeza. O arquivo não traz casa nem período; inferimos pela data do export e pela receita compatível. Está declarado como limitação |
| "Isso funciona para quem não usa Everest?" | Sim, por planilha genérica — é a unidade de demonstração. Integração automática por API está fora do escopo |
| "Por que só uma casa?" | Foi a única com export real cedido. O cliente parou de responder antes de mandar as outras |
| "Os testes rodam contra o Azure SQL?" | Não, rodam em SQLite, por velocidade. Essa diferença já causou um 500 só em produção; hoje há teste que compila as queries no dialeto do SQL Server (`tests/test_dialeto_sql.py`) |
| "Como vocês sabem que é o código novo que está no ar?" | O `/health` informa o SHA do commit publicado, e o workflow só dá sucesso se ele bater com o que acabou de subir |
| "Esses outros negócios são clientes?" | Não, são dado fictício para provar que o cálculo não depende do ramo. Está rotulado "(DEMO)" no nome da unidade. Existem porque não teríamos os dados das outras casas do Saints para hoje |
| "Isso serve para um pequeno negócio?" | Serve para quem tem ficha técnica e inventário mensal, de qualquer porte. Quem não tem esses dois controles não tem o dado que o cálculo exige — atendê-lo seria construir um mini-ERP, que está fora de escopo. Chegamos a apontar para esse público em 06/11 e recuamos: ninguém dele foi entrevistado |
| "Por que vocês mudaram de persona?" | Testamos a hipótese do pequeno negócio contra a evidência que tínhamos e ela não se sustentou. Voltamos ao público com dor comprovada. Está registrado com motivo em `docs/01-requisitos.md`, histórico v1.1 |
| "Dá para saber qual insumo causou o ajuste?" | Em parte. Abaixo do grupo só comparamos o que existe com o mesmo nome nos dois lados: na casa piloto isso dá quatro categorias, todas em BEBIDAS. Em ALIMENTOS não dá, porque o cardápio agrupa por venda (PETISCOS) e as compras por insumo (BOVINOS) — e a tela diz isso, em vez de inventar a granularidade. Chegar ao insumo exigiria a ficha técnica explodida, que é um relatório que não temos |
| "Por que a sugestão de compra é maior que a média de venda?" | Sazonalidade — a coluna "Efeito do mês" mostra quanto aquele mês costuma fugir da média anual para aquele item |
| "Vocês usaram Redis? Cache?" | Não, e de propósito: 10–15 usuários, uso concentrado no fechamento. A recusa está escrita em `docs/09-uso-da-nuvem.md` com o motivo |
| "Cadê a autenticação?" | Não foi entregue. Estava na Sprint 2 e ficou para trás |

## Se algo quebrar na hora

| Sintoma | O que fazer |
|---|---|
| Página demora e não carrega | Cold start. Espere, continue falando do problema (passo 1) e volte. Não recarregue em loop |
| Tela mostra erro de carregar casas | Teste a API direto no `/health`. Se a API responde, é CORS ou o SWA |
| Fechamento devolve 404 | Faltou upload naquele período. Use **09/2026**, que tem os dois lados |
| Nada responde | Vá para o Swagger. Se o Swagger também não responde, mostre os testes verdes no Actions e o código, e diga o que aconteceu. Ambiente cai; mentir sobre isso é pior |
