# Roteiro da demonstração — 100% na nuvem

> Criado em 06/11/2026, depois de uma apresentação em que o projeto foi mostrado
> clonando o repositório numa máquina da faculdade e dependendo de `uv`, Node,
> driver ODBC e `.env` para rodar. **Nada disso é necessário.** A aplicação está
> em produção; a demonstração é um navegador e cinco links.

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
| 2 | O frontend carrega | Abra https://zealous-river-0b6019910.6.azurestaticapps.net |
| 3 | O fechamento calcula | Abra [o fechamento de set/26](https://app-projeto4-saints2026.azurewebsites.net/api/v1/metricas/fechamento?casa_id=2&periodo=2026-09) e confirme `ajuste_pp: -3.68` |
| 4 | Há crédito no Azure | Portal → Cost Management. Se o crédito acabar, tudo cai |

Deixe as abas **já abertas** na ordem do roteiro, numa janela só. Trocar de aba
na frente de alguém é melhor que digitar URL.

> **Se o passo 1 demorar 30–60 segundos:** o Always On do App Service está
> desligado e a instância dormiu. Era o estado até 06/11/2026 e é o que fazia a
> aplicação parecer quebrada. Confira com
> `az webapp config show -g rg-projeto4 -n app-projeto4-saints2026 --query alwaysOn`.

---

## O roteiro (12–15 min)

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

### 2. A aplicação, pelo caminho do usuário (3 min)

https://zealous-river-0b6019910.6.azurestaticapps.net

- **Casas** → o CRUD do RF08. Mostre a casa piloto, o Boteco São Bento - Vila Madalena.
- **Fechamento** → escolha a casa, período **09/2026**, Calcular.

Pare no número e deixe ele respirar:

| | |
|---|---|
| CMV teórico | **25,54%** |
| CMV real | **21,86%** |
| **Ajuste** | **−3,68 pp** |

Os valores em R$ aparecem na tela, ao vivo — e é com eles que o número
convence. Eles **não** estão escritos aqui de propósito: este repositório é
público e faturamento de uma unidade identificada do cliente não vai para o
Git. Leia na tela, não no roteiro.

> "Isto é dado real, do ERP do cliente, sem nenhum tratamento manual. Essa
> divergência de um mês, numa casa só, é exatamente o que a equipe leva dois
> dias para encontrar."

Aponte o valor em R$ na tela ao dizer isso — é o que dá peso à frase.

**Seja preciso sobre o que o número significa.** Ajuste grande, para qualquer
lado, quer dizer "tem erro em algum lugar" — ficha técnica errada, contagem
errada, perda não lançada, desvio. **Não** é dinheiro economizado, e apresentar
como se fosse destrói a credibilidade de todo o resto. O sistema aponta onde
olhar; quem conclui é a equipe de custos.

- Role até **Evolução mensal** → 24 meses de CMV teórico, de set/24 a set/26.
- Role até **Top itens** → onde o custo está concentrado.

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

Ainda em **Fechamento**, troque a casa para **Drogaria Central - Centro (DEMO)**:

- Outro ramo. Categorias **MEDICAMENTOS** e **PERFUMARIA** — nenhuma linha de código conhece esses nomes.
- O dado entrou por **planilha genérica**, não por relatório do Everest.
- **EMBALAGENS** existe só no lado das compras e o sistema o exclui do CMV sozinho — como faz com UTENSILIOS na DRE do restaurante.

Diga que o dado é fictício **antes** de alguém perguntar. O nome da unidade
carrega "(DEMO)" exatamente para isso.

Se o avaliador abrir o código, o argumento se sustenta em dois lugares:

| Arquivo | O que mostrar |
|---|---|
| `app/services/leitores.py` | Três tradutores, uma `LinhaCusto` só. Adaptar a um ERP novo = escrever um tradutor |
| `app/crud.py`, `grupos_comparaveis` | Antes era `GRUPOS_CMV = ("ALIMENTOS", "BEBIDAS")` cravado. Agora é deduzido: comparável é o grupo que os **dois** lados reportam — e na base real devolve exatamente ALIMENTOS e BEBIDAS |

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

- **A API é pública.** Autenticação era RNF03 da Sprint 2 e não foi entregue.
- **A DRE real não diz de qual casa nem de qual mês é.** O rótulo set/26 foi atribuído por nós, com base em evidência circunstancial. É a limitação mais importante do trabalho e está escrita em `docs/01-requisitos.md` 1.9.
- **Um mês de CMV real.** 24 meses de teórico, 1 de real: a série de ajuste tem um ponto.
- **Uma casa real.** O consolidado entre casas é exercitado com a unidade de demonstração.

### 7. CI/CD (opcional, 2 min)

Só se houver tempo e interesse. É aqui que o terminal pode aparecer.

- Aba **Actions** do repositório → `deploy-azure.yml` verde.
- O deploy **não roda sem os testes passarem** (`needs: [testes]`) e **verifica `/health` depois de publicar** — deploy sem verificação é deploy que você descobre quebrado pelo cliente.
- Autenticação por **OIDC**: nenhum segredo de longa duração guardado no GitHub.

---

## Perguntas que provavelmente vêm

| Pergunta | Resposta curta |
|---|---|
| "Esse ajuste de −3,68 pp é economia?" | Não. É divergência entre o que deveria ter custado e o que custou. Para qualquer lado, significa "tem erro em algum lugar" |
| "Como vocês sabem que a DRE é de setembro?" | Não sabemos com certeza. O arquivo não traz casa nem período; inferimos pela data do export e pela receita compatível. Está declarado como limitação |
| "Isso funciona para quem não usa Everest?" | Sim, por planilha genérica — é a unidade de demonstração. Integração automática por API está fora do escopo |
| "Por que só uma casa?" | Foi a única com export real cedido. O cliente parou de responder antes de mandar as outras |
| "Os testes rodam contra o Azure SQL?" | Não, rodam em SQLite, por velocidade. Essa diferença já causou um 500 só em produção; hoje há teste que compila as queries no dialeto do SQL Server (`tests/test_dialeto_sql.py`) |
| "Cadê a autenticação?" | Não foi entregue. Estava na Sprint 2 e ficou para trás |

## Se algo quebrar na hora

| Sintoma | O que fazer |
|---|---|
| Página demora e não carrega | Cold start. Espere, continue falando do problema (passo 1) e volte. Não recarregue em loop |
| Tela mostra erro de carregar casas | Teste a API direto no `/health`. Se a API responde, é CORS ou o SWA |
| Fechamento devolve 404 | Faltou upload naquele período. Use **09/2026**, que tem os dois lados |
| Nada responde | Vá para o Swagger. Se o Swagger também não responde, mostre os testes verdes no Actions e o código, e diga o que aconteceu. Ambiente cai; mentir sobre isso é pior |
