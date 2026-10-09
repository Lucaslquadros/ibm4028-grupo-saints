---
name: sprint-delivery-ibm4028
description: Organizar sprints, issues e entregas parciais do projeto IBM4028 no GitHub Projects - abrir issue no formato de user story, aplicar a Definition of Done, escrever mensagem de commit e descrição de PR, planejar e revisar sprint de 2 semanas, montar o pacote da entrega parcial e preparar a demo para o cliente. Use ao criar issue, abrir PR, planejar ou fechar sprint, preparar entrega parcial, ou definir se um item está pronto. Gatilhos - sprint, issue, user story, GitHub Projects, kanban, backlog, Definition of Done, DoD, pull request, commit, entrega parcial, sprint planning, review, retrospectiva, demo.
---

# Sprints e entregas — IBM4028

Abordagem híbrida da disciplina: **sprints de 2 semanas (Scrum)** + **quadro visual (Kanban)** no GitHub Projects. Fonte: Aula 02.

## Quadro

Colunas: `Backlog` → `To Do` → `In Progress` → `Review` → `Done`

Limite de WIP: no máximo **1 item In Progress por pessoa**. Quadro com tudo em progresso e nada em Done é sinal de sprint mal fatiada, não de time produtivo.

## Papéis no grupo

| Papel | Quem | Faz |
|---|---|---|
| Cliente / stakeholder | Diego Gordon (sócio do Grupo Saints) | Descreve o problema, dá a visão de negócio, valida entregas — representado no time pelo PO |
| Product Owner | Lucas | Prioriza o backlog a partir da visão do cliente, negocia escopo com o time |
| Scrum Master | rotativo entre Pedro e Otávio | Facilita, remove impedimento |
| Dev Team | Lucas, Pedro, Otávio | Executa |

O papel de Scrum Master rodar a cada sprint distribui a responsabilidade — não é cargo.

## Issue = user story

Título: `[RF03] Importar planilha de vendas em CSV`

Corpo:

```markdown
## História
Como analista de estoque,
quero importar a planilha de vendas em CSV,
para não redigitar 200 linhas toda segunda-feira.

## Critérios de aceitação
- [ ] DADO que estou autenticado e na tela de importação
      QUANDO envio um CSV válido de até 10 MB
      ENTÃO vejo o preview das 5 primeiras linhas e o botão "Confirmar"
- [ ] DADO um arquivo com coluna obrigatória faltando
      QUANDO clico em "Enviar"
      ENTÃO recebo erro apontando a coluna, e nada é importado

## Rastreabilidade
Requisito: RF03 (docs/01-requisitos.md)
Prioridade: Must
Sprint: 3

## Definition of Done
- [ ] Código revisado por outra pessoa do grupo
- [ ] Testes automatizados passando
- [ ] Documentado (docstring + /docs atualizado)
- [ ] Deployado no Azure e verificado no ambiente
- [ ] Sem bug crítico conhecido
```

Labels: `must`/`should`/`could`, `rf`/`rnf`, `backend`/`frontend`/`infra`, `sprint-N`.

Toda issue aponta para um requisito numerado. Issue sem RF/RNF atrás é escopo aparecendo pela porta dos fundos.

**INVEST:** se a story não cabe em 1–3 dias, quebre. Se não dá para testar, os critérios não estão escritos.

## Definition of Done — não negociável

Um item só entra em `Done` quando **todos** os cinco valem:

1. **Código revisado** por outra pessoa do grupo
2. **Testes passando** — caminho feliz e o erro
3. **Documentado** — docstring, e o `/docs` reflete a mudança
4. **Deployado no Azure** e verificado no ambiente, não só na máquina de quem escreveu
5. **Sem bug crítico conhecido**

"Funciona na minha máquina" não é Done. "Está no `main`" também não — precisa estar no ar.

## Commits

Conventional Commits, referenciando a issue:

```
feat(itens): adiciona filtro por categoria na listagem

Implementa RF05. Filtro opcional via query param, com índice
na coluna categoria para não varrer a tabela.

Closes #23
```

Prefixos: `feat`, `fix`, `docs`, `test`, `refactor`, `chore`, `ci`.

`Closes #23` fecha a issue e move o card sozinho no Projects.

## Pull Request

```markdown
## O que muda
Uma frase.

## Issue
Closes #23

## Como testar
1. `uv run fastapi dev app/main.py`
2. `GET /api/v1/itens?categoria=alimentacao`
3. Esperado: só itens dessa categoria, `total` coerente

## Checklist
- [ ] Testes novos cobrem caminho feliz e erro
- [ ] `uv run ruff check .` e `uv run pytest` verdes
- [ ] Nenhum segredo no diff
- [ ] `/docs` continua correto
```

PR de mais de ~400 linhas não é revisado de verdade, é aprovado no olho. Quebre.

Regra do semestre: **ninguém aprova o próprio PR.**

## Ritmo da sprint (2 semanas)

| Momento | Quando | Saída |
|---|---|---|
| Planning | Segunda da semana 1 | Sprint Backlog fechado, cards em `To Do` |
| Daily | Diária, 15 min | Fiz / farei / travei |
| Review | Sexta da semana 2 | Demo funcionando **para o cliente** |
| Retrospectiva | Logo após a review | 3 ações concretas com dono |

Sprint Review sem o cliente presente é reunião interna, não review. O feedback dele é o que valida o requisito.

Retrospectiva que produz "comunicar melhor" não produziu nada. Ação de retro tem dono e prazo.

## Entrega parcial

Cada entrega parcial contém:

1. **Documento de requisitos atualizado** (`docs/01-requisitos.md`) — requisito que mudou aparece com o motivo
2. **Repositório** com o board mostrando o que entrou e o que saiu do escopo
3. **Aplicação no ar** com URL funcionando e `/docs` acessível
4. **README** com como rodar local, variáveis necessárias e URL do ambiente
5. **Evidência de validação com o cliente** — data da conversa e o que ele apontou

O que mudou de escopo desde a entrega anterior precisa estar **explícito**, com justificativa. Mudança de requisito é esperada em ágil; mudança silenciosa é escopo fora de controle.

## Métrica

Uma só: **quantos pontos/stories terminaram em Done por sprint** (velocity). Serve para planejar a próxima sprint, não para comparar pessoas.

Se a velocity despenca, o problema quase sempre é story grande demais ou DoD sendo cumprida só no fim.

## Erros que custam nota

| Erro | Consequência |
|---|---|
| Tudo commitado direto na `main` | Sem review, sem histórico de decisão |
| Issue sem critério de aceitação | Ninguém sabe se está pronto |
| Deploy só na véspera da entrega | Todo problema de infra aparece junto |
| Cliente só aparece no início e no fim | Requisito vira chute |
| Todo mundo no mesmo arquivo | Conflito de merge constante |
| Sprint sem retro | O mesmo problema se repete quatro vezes |

## Checklist de fim de sprint

- [ ] Todo card em `Done` cumpre os 5 pontos da DoD
- [ ] Aplicação no ar e `/health` respondendo 200
- [ ] Demo feita para o cliente e feedback registrado como issue nova
- [ ] Retro gerou 3 ações com dono e prazo
- [ ] Backlog repriorizado com o PO
- [ ] `docs/01-requisitos.md` atualizado se algum requisito mudou
