# Ciclo 07/11 a 09/11/2026 — explicar o ajuste

> Criado em 07/11/2026, depois de uma revisão crítica do projeto (Lean
> Inception). **Este documento é a especificação de implementação do ciclo.**
> Quem for implementar (pessoa ou agente) lê este arquivo inteiro antes de
> escrever código, junto com `CLAUDE.md`, `docs/07-fechamento-cmv.md` e as
> skills de `.claude/skills/`.
>
> **Estado: ciclo concluído em 07/11/2026. Todos os itens entregues e no ar**,
> no commit `a7fa9c5`, com a verificação da seção 7 feita. O refinamento de
> 08/11 descrito em 3.8 (fechamento em formato de balanço) **ainda não foi
> publicado** — entra no próximo deploy.
>
> | Item | Estado | Onde |
> |---|---|---|
> | P0 — nomes de grupo padronizados | Entregue | `app/services/leitores.py`, `tests/test_generalizacao.py` |
> | P0 — planilha-modelo `.xlsx` | Entregue | `app/routers/modelos.py`, `tests/test_modelos.py` |
> | 1 — RF11 backend | Entregue | `app/services/explicacao.py`, `app/crud.py`, `app/schemas.py`, `tests/test_explicacao.py`, `tests/test_dialeto_sql.py` |
> | 2 — RF11 tela | Entregue | `frontend/src/screens/Fechamento.tsx`, `frontend/src/api.ts` |
> | 3 — RF12 fluxo guiado | Entregue | `frontend/src/screens/FecharMes.tsx`, `frontend/src/App.tsx` |
> | 4 — RF13 cronômetro | Entregue | `frontend/src/screens/FecharMes.tsx` |
> | Deploy + conferência no `/health` | Feito em 07/11 | ver abaixo |
>
> **Nenhum item precisou da ordem de corte.** Conferido local contra as quatro
> casas DEMO, contra o par Everest sintético (só CHOPP comparado) e contra um
> caso de ajuste negativo; e conferido em produção contra a casa piloto.
>
> **Verificação pós-deploy (07/11), como a seção 7 exige:**
>
> - `/health` → `commit: a7fa9c5a528be34d09e579fa45279cf4949c1fde`, `banco: ok`
> - fechamento de set/26 da casa piloto → `ajuste_pp: -3.68` (inalterado) e
>   `explicacao.situacao: "abaixo"`, `limiar_pp: 1.0`
> - contribuições `BEBIDAS -2,30` + `ALIMENTOS -1,37` = `-3,67`, dentro da
>   tolerância de 0,02 do total — a invariante de 3.1 vale no dado real
> - `grupos_sem_par: []`; 4 subgrupos comparados, **todos em BEBIDAS**, e 36 sem
>   par. É exatamente o que 3.3 previu: em ALIMENTOS as duas taxonomias não se
>   encontram, e a tela declara isso
> - frontend servindo o bundle novo (as cinco abas, com "Fechar o mês")
>
> **Achado do dado real, registrado em `01-requisitos.md` 1.9:** quatro pares de
> subgrupo diferem só no singular/plural (`AGUAS`/`AGUA`, `ENERGETICOS`/
> `ENERGETICO`, `VINHOS`/`VINHO`, `SOBREMESA`/`SOBREMESAS`) e por isso não são
> comparados. O P0 padroniza caixa e espaço, não flexão — e casar flexão é
> heurística de linguagem que, quando erra, inventa desvio. Fica como lacuna
> declarada, não como correção às pressas.

---

## 1. Decisões que este ciclo toma

| # | Decisão | Motivo |
|---|---|---|
| D1 | **Voltam as Personas 1 e 2.** A analista de custos (Persona 1) **alimenta** o sistema; o sócio/diretor (Persona 2) **lê o resultado e decide** | São as únicas personas com entrevista. A Persona 3 (pequeno negócio) foi criada em 06/11 para generalizar a solução, mas generalizar o **formato do dado** não exige mudar de **público**. Ela vira hipótese de mercado futuro, não alvo |
| D2 | **O público é definido pelo dado que ele tem, não pelo porte**: operação com ficha técnica cadastrada e inventário mensal, que exporta uma tabela com grupo, custo e venda | O cálculo depende dos dois lados. Sem ficha técnica não há teórico; sem inventário, o "real" vira "o que comprei" — e o sistema não tem como perceber. Ver a seção "O que o usuário precisa fornecer" em `07-fechamento-cmv.md` |
| D3 | **O valor está em explicar o ajuste, não em mostrá-lo.** O ERP do cliente já tem os números; um número formatado agrega pouco | Diagnóstico da revisão. O sócio entende "CMV subiu 2 pontos"; o que ele não sabe é **onde procurar** |
| D4 | **As casas DEMO continuam**, com o papel declarado: provam que o **formato** e a **regra** são genéricos, não que existe cliente em outros ramos | Sem os dados do Grupo Saints para segunda-feira, o grupo precisava de outros exemplos para mostrar a solução genérica. Isso é legítimo desde que dito |
| D5 | **Não inventar granularidade.** Abaixo do grupo, só se compara o que existe nos dois lados | Ver seção 3.3 — as categorias de compra e de cardápio são taxonomias diferentes |
| D6 | **Sistema encurta o diagnóstico, não previne.** O CMV real depende do inventário do dia 30; o ganho é ter a explicação no dia 1–2 em vez do dia 15 | Delta semanal e alertas ficam como roadmap |

**Fora de escopo deste ciclo:** fluxo sem ERP (mini-ERP), alertas, delta
semanal, autenticação, RF09, mudanças de infra/deploy (salvo se algo quebrar).

---

## 2. Itens, em ordem de prioridade

| Ordem | Item | Requisito | MoSCoW | Estimativa |
|---|---|---|---|---|
| P0 | Pré-requisitos de dado: nomes de grupo padronizados + planilha-modelo `.xlsx` | RF01 | Must | 1,5 h |
| 1 | Explicação do ajuste — backend (decomposição + regras + texto) | **RF11** | Must | 5 h (com testes) |
| 2 | Explicação do ajuste — tela de Fechamento | **RF11** | Must | 2 h |
| 3 | Fluxo guiado "Fechar o mês" | **RF12** | Should | 3,5 h |
| 4 | Tempo do primeiro envio ao resultado | **RF13** | Should | 0,5–1 h |
| — | Docs (`01`, `07`, `08`) com o que foi entregue | — | — | 1,5 h |
| — | Deploys e conferência do commit no `/health` | — | — | 1 h |

**Total: ~15 h.** Para um fim de semana, é apertado.

### Ordem de corte (se não couber até domingo 20h)

1. **Corta o RF12 inteiro.** Maior custo e maior risco, e é o que menos sustenta a tese nova. O cronômetro (RF13) vai para a tela de Upload atual, em 30 min.
2. **Corta a comparação por subgrupo** (3.3). Fica só a contribuição por grupo, com o aviso explícito de que o dado não desce além disso.

**Inegociável:** P0 + itens 1 e 2, com os três ramos de sinal (3.2). Sem isso,
o número da demo (−3,68 pp, real **abaixo** do teórico) contradiz a frase na tela.

### Congelamento

**Nenhum deploy depois de domingo 08/11, 20h.** Depois do último deploy:
`/health` com o SHA do commit novo **e** o fechamento de set/26 da casa piloto
com `ajuste_pp: -3.68` (ver `08-roteiro-demo.md`, "Antes de sair de casa").

---

## 3. RF11 — Explicação do ajuste (especificação)

### 3.1 Contribuição de cada grupo

O `ajuste_pp` de cada grupo usa a **venda do próprio grupo** como denominador
e por isso **não soma** ao ajuste total. Para dizer "principalmente em Y", a
medida é a contribuição em pontos do total:

```
contribuicao_pp(g) = ajuste(g) ÷ venda_liquida(TOTAL) × 100
```

- Com todos os grupos tendo os dois lados, `Σ contribuicao_pp = total.ajuste_pp`
  (tolerância de arredondamento: 0,02). **Teste obrigatório.**
- Se algum grupo tem só um lado no mês (teórico sem real ou o contrário), o
  total fica distorcido por aquele grupo. A explicação **declara** isso em
  `grupos_sem_par` em vez de esconder, e o resumo diz que o total não é
  comparável por completo.
- **Compensação:** se há grupos com contribuições de sinais opostos e as duas
  com |valor| ≥ `LIMIAR_PP`, o resumo diz isso ("ALIMENTOS ficou acima e BEBIDAS
  abaixo; no total, um compensou parte do outro"). Um total pequeno pode
  esconder dois desvios grandes.

### 3.2 Situação e texto: três ramos, nunca dois

O caso real é **negativo** (real abaixo do teórico). Uma frase do tipo
"gastaram X a mais" é falsa para ele. Ajuste negativo **não é economia** — é
divergência (ver `08-roteiro-demo.md`).

`LIMIAR_PP = 1.0` — constante nomeada, declarada como **premissa** (não veio do
cliente), devolvida na resposta para a tela poder exibir.

| `situacao` | Condição (sobre `total.ajuste_pp`) | Leitura | Sugestões (no máximo 2) |
|---|---|---|---|
| `acima` | > +LIMIAR_PP | O custo real ficou acima do que as fichas técnicas previam | 1) Investigar perdas, quebras e desvios em `{grupo principal}` — se houver subgrupo comparado com desvio, nomeá-lo. 2) Conferir se as fichas técnicas de `{grupo principal}` estão com o custo atualizado (ficha subestimada produz o mesmo efeito) |
| `dentro` | entre −LIMIAR_PP e +LIMIAR_PP | Diferença dentro da margem esperada | Nenhuma ação (lista vazia) — mas se houver compensação (3.1), apontar os dois grupos |
| `abaixo` | < −LIMIAR_PP | O custo real ficou **abaixo** do previsto. Não é economia: normalmente indica algo faltando no lado real ou sobrando no teórico | 1) Conferir se todas as compras de `{grupo principal}` do mês foram lançadas e se o inventário de fim de mês não está superestimado. 2) Confirmar que os dois relatórios são do **mesmo período** e conferir as fichas técnicas de `{grupo principal}` (ficha superestimada produz o mesmo efeito) |

`{grupo principal}` = grupo de maior |contribuição| **com o mesmo sinal do total**.

**Público do texto: Persona 2 (sócio).** Sem jargão sem explicação: na primeira
menção, "CMV (custo das mercadorias vendidas)". Os valores em R$ entram no
texto **em tempo de execução** — nunca em teste, doc ou commit com dado da casa
real.

Exemplo de forma (com número sintético):

> "Em 2026-09, o custo real das mercadorias ficou 3,3 pontos acima do previsto
> pelas fichas técnicas (R$ 70,00 a mais). A maior parte veio de MEDICAMENTOS
> (+2,4 pp)."

**A sugestão "contar esses itens semanalmente" não entra:** a Persona 1 já faz
contagem semanal dos itens principais (ver Persona 1 em `01-requisitos.md`).
Para ela, seria ruído.

### 3.3 Subgrupos: só o que existe nos dois lados

**Limite do dado, que a tela precisa dizer:** no Everest, os subgrupos do
cardápio são **categorias de venda** (PETISCOS, CHOPP) e os da DRE de compras
são **categorias de insumo** (BOVINOS, HORTIFRUTI, CHOPP). Não existe "BOVINOS
teórico" sem a ficha técnica explodida em insumos, que o sistema não recebe. E
há um único mês de DRE, então também não há média histórica por categoria.

Atenção: em `exemplos/*.csv` os subgrupos são **idênticos** nos dois lados. A
comparação vai parecer completa nas DEMO e quase vazia na casa real. Isso é
esperado e precisa estar dito na tela, não escondido.

Regra:

- `subgrupos_comparados`: pares (grupo, subgrupo) presentes nos **dois** lados
  do mesmo período, com nome padronizado (P0). Para cada um: custo teórico, custo
  real, ajuste em R$ e ajuste em pp sobre a venda do subgrupo no cardápio.
  Ordenados por |ajuste| decrescente.
- `subgrupos_sem_par`: os demais, com o lado (`teorico` | `real`) e o custo.
  Na tela aparecem como **composição do custo**, nunca como desvio.
- Só grupos do CMV direto (`grupos_comparaveis`).
- A soma roda no banco (`GROUP BY tipo, grupo, subgrupo`), regra 6 do `CLAUDE.md`.

`limite_dado` (texto fixo na resposta): *"O ERP informa compras por categoria
de insumo e vendas por categoria de cardápio. Abaixo do grupo, só comparamos as
categorias que existem com o mesmo nome nos dois relatórios."*

### 3.4 Quando não há explicação

`explicacao` é `null` quando o mês não tem os dois lados (`tem_cardapio` e
`tem_compras`). A tela já mostra o aviso de qual lado falta. Nunca gerar texto
sobre um ajuste que não existe.

### 3.5 Contrato da API (aditivo — o front atual não quebra)

Em `app/schemas.py`:

```python
class ContribuicaoGrupo(BaseModel):
    grupo: str
    ajuste: float = Field(description="custo_real − custo_teorico do grupo, em R$")
    contribuicao_pp: float = Field(description="ajuste ÷ venda total × 100")

class SubgrupoComparado(BaseModel):
    grupo: str
    subgrupo: str
    custo_teorico: float
    custo_real: float
    ajuste: float
    ajuste_pp: float | None  # None se o subgrupo não tem venda no cardápio

class SubgrupoSemPar(BaseModel):
    grupo: str
    subgrupo: str
    lado: Literal["teorico", "real"]
    custo: float

class Explicacao(BaseModel):
    situacao: Literal["acima", "dentro", "abaixo"]
    limiar_pp: float
    resumo: str
    sugestoes: list[str]
    contribuicoes: list[ContribuicaoGrupo]
    grupos_sem_par: list[str]
    subgrupos_comparados: list[SubgrupoComparado]
    subgrupos_sem_par: list[SubgrupoSemPar]
    limite_dado: str

class FechamentoResponse(BaseModel):
    ...  # campos atuais, inalterados
    explicacao: Explicacao | None = None
```

Sem `RootModel`, sem `...` como default, estilo `Annotated` nas rotas (regras 2
e 3 do `CLAUDE.md`). O campo é opcional e novo: o frontend em produção continua
funcionando entre o deploy do backend e o do front.

### 3.6 Onde cada coisa vai

| Arquivo | Mudança |
|---|---|
| `app/services/explicacao.py` (novo) | Funções **puras**, sem banco: contribuições, situação, compensação, texto e sugestões. `LIMIAR_PP` e `LIMITE_DADO` como constantes nomeadas. Testável sem fixture |
| `app/crud.py` | `subgrupos_por_lado(db, casa_id, periodo, grupos)` → `[(tipo, grupo, subgrupo, custo, venda)]` com `GROUP BY` no banco, `nivel == "subgrupo"` |
| `app/routers/metricas.py` | A rota de fechamento monta `explicacao` quando há os dois lados |
| `app/schemas.py` | Classes da seção 3.5 |
| `tests/test_explicacao.py` (novo) | Ver 3.7 |
| `tests/test_dialeto_sql.py` | Compilar a query nova no dialeto do SQL Server (o motivo está no próprio arquivo: já houve 500 só em produção) |
| `frontend/src/api.ts` | Tipos novos, `explicacao` opcional |
| `frontend/src/screens/Fechamento.tsx` | Parágrafo do resumo **no topo** (acima do hero), sugestões, coluna "contribuição" na tabela de grupos, bloco de subgrupos comparados, `limite_dado` visível sempre que houver subgrupos sem par |

### 3.7 Testes (cada critério GWT vira teste — regra 7)

Usar as planilhas sintéticas de `tests/planilhas.py`. O par Everest sintético
já reproduz o limite real: PETISCOS (cardápio) não tem par em BOVINOS/HORTIFRUTI
(DRE); CHOPP existe nos dois.

| Caso | Esperado |
|---|---|
| Ajuste total > +1 pp (farmácia sintética, +3,33 pp) | `situacao == "acima"`, resumo cita o grupo principal, ≤ 2 sugestões |
| Ajuste total < −1 pp | `situacao == "abaixo"`, resumo **não** contém "economia" nem "a mais", sugestão menciona compras não lançadas/inventário |
| Ajuste entre −1 e +1 pp | `situacao == "dentro"`, `sugestoes == []` |
| Grupos com sinais opostos acima do limiar | Resumo menciona compensação e os dois grupos |
| Soma das contribuições | Bate com `total.ajuste_pp` (± 0,02) |
| Só um lado no mês | `explicacao is None`, resposta 200 com o resto do fechamento |
| Grupo com só um lado num mês com os dois relatórios | Aparece em `grupos_sem_par` |
| Everest sintético | `subgrupos_comparados` = só CHOPP; PETISCOS, BOVINOS e HORTIFRUTI em `subgrupos_sem_par` |
| Casa/período inexistente | Mantém 404 atual |
| Fechamento de set/26 da casa real | **Não testável no Git** (dado real). Conferir à mão após o deploy: `ajuste_pp` continua −3,68 |

### 3.8 Decisões tomadas na implementação (07/11)

Três pontos que a especificação deixava em aberto e que o código precisou fechar:

1. **Compensação com o total "dentro" entra no resumo, não nas sugestões.** A
   tabela de 3.2 dizia "apontar os dois grupos" na coluna de sugestões, mas o
   teste obrigatório exige `sugestoes == []` nesse ramo — e 3.1 já pede a frase
   no resumo. Vale a leitura de 3.1: dentro da margem não gera ação.
2. **Com grupo sem par, a frase vira "entre os grupos com os dois lados, o
   maior desvio veio de X".** Quando o total é puxado por um grupo que só tem
   um lado, "a maior parte veio de X" descreveria mal o número — o grupo
   nomeado pode responder por uma fração pequena dele. A frase então se limita
   ao que é de fato comparável, e a declaração de `grupos_sem_par` explica o
   resto.
3. **Sem nenhum grupo no mesmo sentido do total, não há "grupo principal".** O
   texto não afirma direção, e a única sugestão é enviar o relatório que falta.
   Nomear o maior desvio em módulo apontaria para o lado oposto ao do número.

**Refinamento de 08/11, depois de usar a tela com o dado real:** a tabela de
grupos virou um **balanço** — colunas são os dois lados (teórico / real /
diferença) e linhas são as contas, com os subgrupos comparáveis aninhados e a
composição do custo recolhida. A tabela anterior punha venda, CMV teórico e CMV
real na mesma linha, e "CMV real" é custo de **compras** sobre receita de
**venda**: dois relatórios misturados numa linha só, correto no cálculo e
ilegível na tela. No formato novo a venda aparece uma vez, como base do grupo, o
que torna visível que é o mesmo denominador dos dois lados. A coluna
"contribuição" saiu da tabela (é análise, não balanço; o resumo já nomeia o
grupo de maior peso) e o hero perdeu o par teórico × real, que passou a estar no
TOTAL. O ganho não foi só estético: o balanço revelou **DESTILADOS +38,24 pp**
dentro de BEBIDAS, um subgrupo fortemente positivo escondido num grupo que fecha
negativo, invisível no formato anterior.

E uma correção que não estava prevista: a tela marcava qualquer ajuste ≤ 0 como
**"Favorável"**, em verde. Era a contradição que 3.2 descreve, já no ar — o
painel diria ao sócio que o mês foi bom exatamente no caso de set/26. Agora o
selo tem os três estados, e "abaixo" é âmbar de atenção.

---

## 4. P0 — Pré-requisitos de dado

Duas lacunas encontradas ao escrever o contrato de entrada (seção "O que o
usuário precisa fornecer" em `07-fechamento-cmv.md`).

### 4.1 Nomes de grupo e subgrupo padronizados

Hoje os tradutores só tiram espaços das pontas (`_texto`). `Alimentos` num lado
e `ALIMENTOS` no outro viram grupos diferentes, e o grupo **some do CMV sem
erro**. Padronizar na leitura, nos três tradutores: maiúsculas e espaços
internos colapsados (`" ".join(texto.upper().split())`). Manter acento — é
nome exibido.

- Risco para produção: nenhum esperado. Os exports do Everest e os `exemplos/`
  já vêm em maiúsculas; a regra só afeta uploads novos.
- Teste: planilha genérica com `Alimentos` de um lado e `ALIMENTOS ` do outro
  entra no CMV direto.

### 4.2 Planilha-modelo em `.xlsx`

A API aceita só `.xlsx` (415 para o resto). Os `exemplos/*.csv` só funcionam
porque `scripts/popular_demo_generico.py` converte antes de enviar. E o
`.gitignore` bloqueia `*.xlsx` de propósito (dado de cliente nunca entra no Git)
— não abrir exceção.

Solução: endpoint que **gera** o modelo na hora, com linhas sintéticas.

- `GET /api/v1/modelos/{tipo}` (`tipo` = `cardapio` | `compras`) → `.xlsx` com
  o cabeçalho da tabela C de `07-fechamento-cmv.md` e 3–4 linhas de exemplo
  sintético. 422 para `tipo` inválido (validação do `Literal`).
- Arquivos: `app/routers/modelos.py` (novo), registrar em `app/main.py`,
  `tests/test_modelos.py` (200 com content-type xlsx; o arquivo baixado,
  reenviado ao upload, é aceito com 201; tipo inválido → 422).

---

## 5. RF12 — Fluxo guiado "Fechar o mês"

**Regra: não quebrar o fluxo atual nem os dados em produção.**

- **Aba nova** `Fechar o mês` (`frontend/src/screens/FecharMes.tsx`), em
  `App.tsx`. As abas Casas, Upload, Fechamento e Quanto comprar ficam como estão.
- Passos: **1. casa e período → 2. lado teórico → 3. lado real → 4. resultado**
  (reaproveita o componente de Fechamento).
- Em cada passo de envio: a tabela de colunas daquele lado (C de `07`), o botão
  "Baixar planilha-modelo" (endpoint 4.2) e a frase "o export do Everest também
  é aceito como está".
- **Reenvio substitui o anterior** (restrição única casa + período + tipo). Se
  já existe upload do passo, o padrão é **"usar o já enviado"** (pular); substituir
  exige confirmação explícita.
- **Na demo, usar uma casa DEMO ou um período novo. Nunca a casa piloto em
  09/2026** — o fluxo sobrescreveria o dado real ao vivo.

## 6. RF13 — Tempo do primeiro envio ao resultado

Os "2 dias" são trabalho humano **declarado** pelo cliente, nunca medido. Os
segundos do sistema são outra coisa. Comparar os dois sem dizer isso é um flanco
aberto para a banca.

- Medir **no frontend**, tempo de relógio: do envio do primeiro arquivo do fluxo
  até o resultado aparecer na tela (`performance.now()`). Mostrar ao fim:
  "Do primeiro envio ao resultado: X s".
- Ao lado, a ressalva fixa: "não inclui o tempo de exportar os relatórios do ERP".
- Sem tabela nova, sem migração. Se o RF12 for cortado, o cronômetro vai para
  a tela de Upload atual (do envio até a resposta 201).

---

## 7. Regras do ciclo

- **Nenhum valor em R$ da casa real** no Git, em testes ou em docs. Percentuais e pp podem (nota de confidencialidade em `01-requisitos.md` 1.9).
- Teste para cada regra nova, caminho feliz e erro. `uv run ruff check .` e `uv run pytest` verdes antes de cada commit.
- Commits pequenos, um por item. Mensagem no formato da skill `sprint-delivery-ibm4028`.
- Ordem de deploy: **backend primeiro** (campo novo é opcional), conferir `/health`; depois o frontend.
- Depois de cada deploy: `/health` com o SHA novo + fechamento de set/26 com `ajuste_pp: -3.68`.
- No fim: marcar como entregue em `01-requisitos.md` (RF11–RF13) e reescrever o passo 2 de `08-roteiro-demo.md` com o que **está no ar**.

## 8. Roadmap (não implementar agora)

| Item | Por que fica para depois |
|---|---|
| Delta semanal | Exige inventário parcial semanal, que hoje não chega ao sistema |
| Alertas durante o mês | Mesmo motivo; e sem auth não há para quem mandar |
| Persona 3 (pequeno negócio) | Hipótese não entrevistada; exige resolver ficha técnica e inventário antes (mini-ERP) |
| Ficha técnica explodida em insumos | É o que permitiria comparar BOVINOS teórico × real — exige um novo relatório do ERP |
