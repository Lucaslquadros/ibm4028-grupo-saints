---
name: requisitos-ibm4028
description: Escrever, revisar e priorizar o documento de requisitos do projeto IBM4028 (IBMEC CDIA). Use ao redigir visão geral, stakeholders, personas, requisitos funcionais (RF) e não funcionais (RNF), user stories no formato Como/quero/para, critérios de aceitação Given-When-Then, priorização MoSCoW, restrições e glossário. Use também ao revisar requisito vago, não testável, sem prioridade, ou que esconde solução técnica no lugar do problema. Gatilhos - documento de requisitos, entrega parcial 1, RF, RNF, user story, critério de aceitação, MoSCoW, persona, stakeholder, escopo do MVP, definir o problema, customer discovery, Mom Test.
---

# Requisitos — IBM4028

Base da **Entrega Parcial 1**. Fonte: Aula 02 (Do problema aos requisitos) e Aula 03 (Oficina 1).

## Antes de escrever qualquer requisito

Requisito sem evidência atrás é chute. O ciclo é:

**Hipótese → Conversa → Evidência → Requisito.**

Só vire requisito o que passou pelas quatro etapas. O que não tiver evidência volta a ser hipótese para a próxima conversa com o cliente.

### O projeto tem cliente — regra do semestre

Alguém precisa ocupar o papel: dono de negócio, gestor de ONG, setor do IBMEC, profissional do setor. O papel é **ativo**: descreve o processo de hoje, prioriza, valida cada entrega parcial e confirma no fim se o problema foi resolvido.

Sem essa pessoa, o projeto vira exercício de programação.

### A dor é real? Analgésico ou vitamina

| Sinal de dor real (analgésico) | Sinal de "seria bom ter" (vitamina) |
|---|---|
| Acontece toda semana | Acontece de vez em quando |
| Custa tempo, dinheiro ou cliente perdido | Ninguém perde nada hoje |
| **Já existe gambiarra**: planilha, WhatsApp, caderno | Não há solução alternativa em uso |
| Já tentaram resolver e não deu certo | Ninguém procurou resolver |
| A pessoa devolve a ligação sem insistência | Interesse morre depois da 1ª conversa |

O melhor sinal é a gambiarra. Se a pessoa inventou um jeito trabalhoso de contornar, o problema existe.

### Mom Test: pergunte sobre o passado, não sobre a ideia

| Não pergunte | Pergunte |
|---|---|
| "Você usaria um app que faz isso?" | "Me conta como você faz isso hoje." |
| "Você acha a ideia boa?" | "Quando foi a última vez que deu problema?" |
| "Você pagaria R$ 50/mês?" | "Quanto isso já te custou em dinheiro?" |
| "Controlar estoque é um problema, né?" | "O que você já tentou para resolver?" |

Elogio não é evidência. Comportamento passado é.

## Formato do problema

> "**[Persona]** precisa de **[necessidade]** porque **[insight]**."

Se o problema não menciona **quem sofre**, **qual a dor** e **qual o impacto**, ele não está definido.

| ✘ Mal definido | ✔ Bem definido |
|---|---|
| "Precisamos de um app" | "Analistas gastam 4h/dia coletando dados de 5 fontes manualmente" |
| "Vamos usar machine learning" | "Gestores não têm visibilidade de vendas por região em tempo real" |
| "Queremos um dashboard" | "O time leva 3 dias para gerar relatórios que precisariam ser diários" |

## Estrutura obrigatória do documento (10 seções)

1. **Visão Geral** — objetivo, contexto, justificativa, escopo
2. **Stakeholders** — partes interessadas e responsabilidades
3. **Personas** — 2 a 3, com dores e objetivos específicos
4. **RF** — numerados RF01, RF02…
5. **RNF** — numerados RNF01, RNF02…
6. **User Stories** — Como/quero/para + critérios GWT
7. **Priorização** — MoSCoW de cada requisito
8. **Arquitetura Cloud** — serviços Azure escolhidos **e a justificativa**
9. **Restrições** — técnicas, prazo, budget, LGPD
10. **Glossário** — termos técnicos e de negócio

O arquivo do projeto é `docs/01-requisitos.md`. Preencha ali, não crie documento novo.

## Personas — template

| Campo | Exemplo |
|---|---|
| Nome e cargo | Maria, Analista de Dados Jr. |
| Contexto | 2 anos de experiência, Excel e Python básico, equipe de 5 |
| Comportamentos | Acessa 3x/dia, usa mobile em campo, prefere exportar para Excel |
| Dores | Dados espalhados, relatório manual, erro de input |
| Objetivos | Automatizar coleta, dashboard em tempo real, alerta por e-mail |
| Cenário de uso | Toda segunda gera relatório semanal: 4h hoje, quer 10 min |
| Frase-chave | "Perco mais tempo juntando dados do que analisando." |

## RF e RNF

**RF** = o que o sistema faz. **RNF** = como ele se comporta. Ambos precisam ser testáveis.

Categorias de RNF que o projeto cloud exige: performance, segurança, disponibilidade, escalabilidade, usabilidade, manutenibilidade.

### Formato

```
RF03 — Upload e processamento de arquivo CSV
Prioridade: Must
Descrição: O usuário envia um CSV de até 10 MB; o sistema valida colunas
           obrigatórias e devolve preview antes de confirmar a importação.
Origem: entrevista com [cliente] em [data]
```

```
RNF01 — Tempo de resposta
Prioridade: Should
Métrica: 95% das requisições GET respondem em < 2s medidas no Application Insights
```

### Requisitos cloud a definir cedo (impactam custo e arquitetura)

| Dimensão | Pergunta | Decide |
|---|---|---|
| Volume de dados | Quantos registros? GB/mês? | Azure SQL × Cosmos DB × Data Lake |
| Usuários simultâneos | Picos previsíveis? | Tier do App Service, auto-scaling |
| Disponibilidade | 24/7 ou horário comercial? | SLA, redundância, região, backup |
| Sensibilidade | Dado pessoal (LGPD)? Financeiro? | Criptografia, Key Vault, base legal |
| Orçamento | Free tier basta? | Tiers, alertas de custo |
| Integrações | API externa? Import/export? | Gateway, filas, versionamento |

## MoSCoW

| Nível | Significado | Fatia | Exemplo |
|---|---|---|---|
| **Must** | Sem isso o projeto falhou | ~60% | Autenticação, CRUD principal, deploy funcional |
| **Should** | Importante, não crítico | ~20% | Filtro avançado, exportar PDF, notificação |
| **Could** | Desejável se sobrar tempo | ~15% | Tema dark, drag & drop, tutorial |
| **Won't** | Fora do escopo, documentado | ~5% | App mobile nativo, integração com IA |

**Must = MVP.** Só passe para Should quando todos os Must estiverem entregues.

Se tudo é Must, nada é Must.

## User Stories — INVEST + Given-When-Then

```
Como analista de estoque,
quero importar a planilha de vendas em CSV,
para não redigitar 200 linhas toda segunda-feira.

Critérios de aceitação:
  DADO que estou autenticado e na tela de importação
  QUANDO seleciono um CSV válido de até 10 MB e clico em "Enviar"
  ENTÃO vejo o preview das 5 primeiras linhas e o botão "Confirmar"

  DADO que selecionei um arquivo com coluna obrigatória faltando
  QUANDO clico em "Enviar"
  ENTÃO recebo erro apontando qual coluna faltou, e nada é importado
```

INVEST: **I**ndependent, **N**egotiable, **V**aluable, **E**stimable, **S**mall (1–3 dias), **T**estable.

Cada story precisa de **2 a 5 critérios GWT** — eles viram os testes automatizados. Um GWT bom mapeia direto para um teste em `tests/`.

## Revisão — erros que reprovam o requisito

| Erro | Sintoma | Correção |
|---|---|---|
| Vago | "O sistema deve ser rápido" | "Resposta < 2s para 95% dos GET" |
| Não testável | "A interface deve ser bonita" | "Seguir design system, componentes Tailwind" |
| Solução disfarçada | "Usar Redis para cache" | "Tempo de resposta < 500ms para dados frequentes" |
| Escopo infinito | "O sistema deve fazer tudo" | "RF01–RF08 são Must para o MVP" |
| Ignorar RNF | Só lista funcionalidade | Definir SLA, performance, segurança, backup |
| Sem prioridade | "Tudo é importante" | Aplicar MoSCoW |

**Regra de ouro: se não dá para escrever um teste para o requisito, ele não está escrito.**

## Checklist antes de entregar

- [ ] Existe alguém nomeado no papel de cliente, com data das conversas registradas
- [ ] O problema cabe em uma frase no formato Persona + necessidade + insight
- [ ] Há evidência (não opinião) por trás de cada Must
- [ ] As 10 seções estão preenchidas — nenhuma com "a definir"
- [ ] Todo RF e RNF tem ID, prioridade MoSCoW e é testável
- [ ] Toda user story tem 2–5 critérios GWT
- [ ] Os Must cabem no MVP de 14 semanas: 1 CRUD completo, 1 upload, 1 dashboard
- [ ] A seção de arquitetura cita os serviços Azure **com justificativa**, não só o nome
- [ ] Restrições incluem LGPD se houver qualquer dado pessoal
