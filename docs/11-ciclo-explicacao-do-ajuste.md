# Ciclo 07/11 a 09/11/2026 — explicar o ajuste

> Criado em 07/11/2026, depois de uma revisão crítica do projeto (Lean
> Inception). **Este documento é a especificação de implementação do ciclo.**
> Quem for implementar (pessoa ou agente) lê este arquivo inteiro antes de
> escrever código, junto com `CLAUDE.md`, `docs/07-fechamento-cmv.md` e as
> skills de `.claude/skills/`.
>
> **Estado: especificado, nada implementado.** Replanejado no fim do dia 07/11/2026: entram
> o RF14 (Blob lido) e o RF09 (nota fiscal, condicional); sai o RF12. Cada item muda para "entregue"
> aqui e em `docs/01-requisitos.md` só depois do deploy conferido no `/health`.

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

| D7 | **O Blob passa a ser lido, não só escrito.** Cada número do fechamento aponta para o arquivo que o gerou (RF14), com download por SAS de curta duração | Auditoria em `09-uso-da-nuvem.md`: hoje a URL guardada devolve 401 e nenhuma tela lê o Blob. É o pré-requisito de qualquer uso com imagem |
| D8 | **Imagem só com função: nota fiscal como prova do lado real (RF09).** Não "foto para justificar o Blob" | Para o Blob, planilha e foto são o mesmo tipo de coisa (binário). O que justifica a foto é ela responder a uma pergunta do fechamento: a sugestão do ramo `abaixo` do RF11 é "conferir se todas as compras foram lançadas" — a nota é a prova. Atualizada no fim de 07/11 (a primeira revisão do mesmo dia tinha tirado o RF09 do ciclo) |

**Fora de escopo deste ciclo:** fluxo sem ERP (mini-ERP), alertas, delta
semanal, autenticação, RF12 (cortado em 07/11), mudanças de infra/deploy
(salvo se algo quebrar).

---

## 2. Itens, em ordem de prioridade

> **Replanejado no fim de 07/11/2026 (sábado).** O RF12 saiu do ciclo e entraram o
> RF14 (rastreabilidade pelo Blob) e o RF09 (nota fiscal) como item condicional.
> A ordem abaixo é a de execução.

| Ordem | Item | Requisito | MoSCoW | Estimativa | Deploy |
|---|---|---|---|---|---|
| 1 | P0 — nomes de grupo padronizados + planilha-modelo `.xlsx` | RF01 | Must | 1,5 h | junto com 2 |
| 2 | Explicação do ajuste — backend + testes | **RF11** | Must | 5 h | **deploy 1 (backend)** |
| 3 | Explicação do ajuste — tela de Fechamento + cronômetro na tela de Upload | **RF11**, **RF13** | Must / Should | 2,5 h | **deploy 2 (front)** |
| 4 | "De onde veio este número": download do arquivo original por SAS | **RF14** | Should | 2 h | deploy 3 (back + front) |
| 5 | Nota fiscal fotografada no período (versão enxuta, seção 4c) | **RF09** | Could neste ciclo | 4 h | deploy 4 — **só se 1–4 estiverem no ar até domingo 12h** |
| — | Docs (`01`, `07`, `08`) com o que foi entregue | — | — | 1 h | — |

**Total: ~16 h, com 4 h condicionais.** Cabe no fim de semana só se nada travar; a ordem
existe para que o que ficar de fora seja sempre o final da fila.

### Ordem de corte

1. ~~RF12 inteiro~~ — **já cortado em 07/11.** O cronômetro (RF13) foi para a tela de Upload (seção 6).
2. **RF09** — se no domingo às 12h os itens 1–4 não estiverem no ar, ele vira "especificado, próximo passo" na apresentação. A especificação em `10-anexos-de-imagem.md` sustenta a fala.
3. **Comparação por subgrupo** (3.3). Fica só a contribuição por grupo, com o aviso de que o dado não desce além disso.
4. **RF14.** Só se o RF11 estiver atrasado.

**Inegociável:** itens 1–3, com os três ramos de sinal (3.2). Sem isso, o
número da demo (−3,68 pp, real **abaixo** do teórico) contradiz a frase na tela.

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

## 4b. RF14 — De onde veio este número (Blob lido, não só escrito)

Hoje `UploadCusto.url` guarda a URL nua do blob, que devolve **401** (o
container é privado, corretamente). E ao reenviar, o original é apagado — só o
soft delete de 14 dias o segura. Nenhuma tela lê o Blob.

- **Endpoint:** `GET /api/v1/uploads-custo/{upload_id}/arquivo`
  - Com Azure: **302** para uma URL SAS de **leitura**, válida por **5 min**, com escopo de **um blob** (`generate_blob_sas`, permissão `read`). A chave vem da connection string já configurada — nada de segredo novo.
  - Sem Azure (dev/testes): **200** com o arquivo de `uploads_local/` (`FileResponse`), `Content-Disposition` com o `nome_original`.
  - **404** se o upload não existe ou o arquivo sumiu. Erro do SDK vai para o log, nunca para a resposta (regra 9).
- **Arquivos:** `app/services/storage.py` (`url_leitura(blob_name, nome_original)`), `app/routers/uploads.py` (rota), `tests/test_uploads.py` (200 local com os mesmos bytes enviados; 404 para id inexistente).
- **Tela:** no Fechamento, bloco **"De onde veio este número"** com os dois uploads do período (lado, nome original, data de envio, botão "Baixar original"). Os ids vêm de `GET /api/v1/uploads-custo?casa_id=&periodo=`, que já existe.
- **Não mudar agora:** o comportamento de apagar o blob antigo no reenvio. Guardar versões é o passo seguinte (registrado em 8. Roadmap).
- **Por que vale:** a banca pode perguntar "como o sócio sabe que o número está certo?". A resposta passa a ser "abra o arquivo que o gerou". E o SAS demonstra privilégio mínimo: um arquivo, leitura, minutos.

## 4c. RF09 — Nota fiscal fotografada (versão enxuta, condicional)

**Só começa se os itens 1–4 estiverem no ar até domingo 08/11, 12h.** Especificação
completa em `10-anexos-de-imagem.md`; aqui está o recorte que cabe em 4 h.

A foto tem função: ela é a **prova** que o fechamento pede. No ramo `abaixo`
do RF11, a sugestão é conferir se todas as compras foram lançadas; no ramo
`acima`, investigar o grupo que mais contribuiu. Nos dois casos, a pergunta
seguinte é "cadê a nota?".

Entra:

- Tabela `Anexo` como em `10-anexos-de-imagem.md` (`create_all` cria a tabela nova no startup; nenhuma tabela existente muda).
- `POST /api/v1/casas/{casa_id}/anexos` (multipart: `periodo`, `descricao` opcional, `arquivo`) → **201** · 404 casa · 413 · 415.
- `GET /api/v1/casas/{casa_id}/anexos?periodo=` → 200 **paginado** (regra 6).
- `GET /api/v1/anexos/{id}/conteudo` → 302 SAS / 200 local, reaproveitando o RF14.
- **Validação por magic bytes** no servidor: só JPEG, PNG e WebP. SVG recusado (415), mesmo com extensão de imagem. Nome do blob em `uuid4` (regra 10).
- **No navegador, antes de enviar:** reduzir para no máximo 1600 px no lado maior e reencodar em JPEG via `<canvas>`. Isso resolve o limite de 10 MB **e remove o EXIF** (localização do celular), sem adicionar Pillow ao backend.
- Tela: seção **"Notas do mês"** no Fechamento, ao lado do "De onde veio este número", com miniaturas e botão "Anexar nota".
- Testes: 201 com PNG sintético gerado no teste; 415 para SVG e para texto renomeado `.jpg`; 404 casa inexistente; listagem paginada filtrando por período.

Fica fora: DELETE, OCR, vínculo da nota a um grupo, várias fotos por envio.

**Na demo:** anexar numa casa **DEMO**. Não usar foto de nota real do cliente
(tem CNPJ e valores) — use uma nota fictícia ou um cupom pessoal sem dados
sensíveis.

## 5. RF12 — Fluxo guiado "Fechar o mês" (cortado em 07/11)

> **Fora do ciclo.** Mantido como especificação para depois. O RF14 entrou no
> lugar: custa menos e responde a uma pergunta mais provável da banca.

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
- Sem tabela nova, sem migração.
- **Como o RF12 foi cortado, este é o formato do ciclo:** cronômetro na tela de
  Upload atual, do clique em enviar até a resposta 201 (o arquivo já traduzido e
  gravado). Mostrar "Arquivo lido e gravado em X s" com a mesma ressalva.

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
| Versões dos uploads no Blob | Hoje reenviar apaga o original (soft delete segura 14 dias). Guardar versões permitiria mostrar "o fechamento mudou porque o arquivo foi reenviado em tal data" |
| Registro de perda/quebra com foto | Outra imagem com função (a foto é a prova da perda), ligada ao ramo `acima` do RF11. Ideia em `10-anexos-de-imagem.md`, não especificada |
| RF12 — fluxo guiado | Cortado em 07/11; especificação na seção 5 |
