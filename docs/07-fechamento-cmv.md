# Fechamento de CMV: como os dados entram e como o cálculo é feito

> Criado em 03/11/2026, depois da Conversa 2 (Marcela, operação/custos) e da
> análise dos exports reais do Everest enviados por ela em 23/10.

## O problema que o sistema automatiza

Todo mês, para cada casa, a equipe de custos monta à mão um relatório de
fechamento (cerca de **2 dias**), cruzando exports de três módulos do Everest
(vendas, compras e materiais):

- **CMV teórico**, ou CMV de cardápio: vendas × custo da ficha técnica. Feito pela Joyce.
- **CMV real**, ou CMV de compras: custo de compras **depois do inventário completo do dia 30**. Feito pelo Wellington.
- **Ajuste teórico** = real − teórico. Quando ele é grande, "tem erro em algum lugar" (ficha técnica, contagem, perda não lançada, desvio).

Quem usa: a analista de custos (Persona 1) **envia** os relatórios; o
sócio/diretor (Persona 2) **lê** o fechamento e decide. Ver `01-requisitos.md`,
seção 3.

## O que o usuário precisa fornecer

> Adicionado em 07/11/2026. É o contrato de entrada do sistema: se algo desta
> seção faltar, o fechamento sai errado ou não sai. Está escrito para que a
> afirmação "a solução é genérica" tenha fronteira clara.

### A. Antes de qualquer arquivo — o que a operação precisa ter

O sistema não supre estes itens: eles nascem na operação.

| Pré-requisito | Por quê | Se faltar |
|---|---|---|
| **Ficha técnica cadastrada** para os itens vendidos | É ela que gera o custo teórico (venda × custo-padrão) | Não existe lado teórico, logo não existe fechamento |
| **Inventário de fim de mês fechado antes de exportar o lado real** | CMV real = estoque inicial + compras − estoque final | O "real" vira "o que comprei no mês". O sistema **não percebe** e calcula um ajuste sem sentido |
| **As mesmas categorias (grupos) nos dois relatórios** | Só entram no CMV os grupos que aparecem nos dois lados | Grupo com nome diferente em cada lado sai do cálculo em silêncio. Desde 07/11, diferença só de caixa ou de espaço não conta como nome diferente |
| **Uma unidade por arquivo** | O fechamento é por unidade | Arquivo consolidado de várias unidades não tem como ser separado |

Esta é a fronteira do público: **operações com ficha técnica e inventário
mensal**, de qualquer ramo, que exportam uma tabela com grupo, custo e venda. O
porte não importa; o dado, sim.

### B. Em cada envio

| Campo | Regra |
|---|---|
| Unidade | Cadastrada antes (aba Casas) |
| Período | `AAAA-MM`. **O arquivo não informa o período: quem declara é o usuário** |
| Lado | `cardapio` (teórico) ou `compras` (real). O **formato** do arquivo é detectado sozinho |
| Arquivo | **Só `.xlsx`**, até 10 MB. Com várias abas, uma delas precisa começar com o mês do período (ex.: `SETEMBRO26`) |
| Reenvio | Substitui o anterior da mesma unidade, período e lado |

### C. Conteúdo de cada lado (planilha genérica)

| Coluna (sinônimos aceitos) | Lado teórico | Lado real | Usada em |
|---|---|---|---|
| `grupo` (`categoria`) | **Obrigatória** | **Obrigatória** | Tudo |
| `custo` (`custo total`) | **Obrigatória** | **Obrigatória** | Tudo |
| `venda_liquida` (`venda`, `receita`, `faturamento`) | **Na prática obrigatória**: é o denominador do CMV % dos dois lados | Opcional; usada só se o mês não tiver lado teórico | CMV %, ajuste em pp |
| `subgrupo` (`subcategoria`) | Opcional | Opcional | Detalhamento (ver "Explicação do ajuste") |
| `item` (`produto`, `descricao`) + `quantidade` (`qtd`) | Opcional no fechamento; **obrigatória para "Quanto comprar"** | Ignorada | Top itens, RF07 |

Colunas achadas pelo nome, em qualquer ordem; colunas a mais são ignoradas;
números no formato `1.234,56` são aceitos. Os dois relatórios do Everest
(engenharia de cardápio e DRE de compras) são lidos como saem, sem preparo.

### D. Para a recomendação de compra (RF07)

| Meses de lado teórico | O sistema consegue |
|---|---|
| < 3 | Sugestão com confiança "baixa" |
| 3 | Média móvel |
| 6 | + tendência |
| 12 | + sazonalidade |

Os **nomes dos itens precisam ser iguais entre os meses**: item renomeado no
ERP parte a série em dois sem aviso (`01-requisitos.md` 1.9).

### O que o sistema aceita sem conferir

Onde a "solução genérica" pode falhar **sem dar erro**:

1. **Se o lado real é pós-inventário.** Nada no arquivo indica.
2. **Se o período declarado é o do arquivo.** É a limitação da DRE do caso de origem, e vale para qualquer usuário.
3. ~~**Maiúsculas e espaços no nome do grupo.**~~ **Resolvido em 07/11** (P0 do ciclo): os três tradutores padronizam nome de grupo e subgrupo na leitura — maiúsculas e espaços internos colapsados, acento preservado por ser nome exibido. `Alimentos` e `ALIMENTOS ` passam a ser o mesmo grupo. Só vale para o que for carregado a partir daí.
4. **Sinal e unidade dos valores.** Se o ERP exportar custo como negativo, o ajuste sai invertido.

## Os dois relatórios que o sistema lê

| `tipo` | Relatório do Everest | Lado do fechamento |
|---|---|---|
| `cardapio` | Engenharia de cardápio | CMV teórico |
| `compras` | DRE gerencial de compras | CMV real |

São **relatórios de impressão exportados para Excel**, não tabelas: têm
cabeçalho de empresa, totais misturados com itens e hierarquia por posição ou
código. Cada um tem um tradutor em `app/services/leitores.py`, e os dois
produzem a **mesma** linha (`LinhaCusto`: nível, grupo, subgrupo, nome,
quantidade, venda líquida, custo). É isso que permite cruzar os dois com um
`GROUP BY`.

### Engenharia de cardápio

- Linha de títulos com `Q. Venda`, `V. Venda Líquida` e `Custo Geral`, localizada por nome e não por posição.
- Coluna A preenchida = **grupo** (ALIMENTOS, BEBIDAS…) quando a linha seguinte também tem coluna A; senão, é **subgrupo** (PETISCOS, CHOPP…).
- Coluna A vazia + coluna B preenchida = **item** vendido.
- O primeiro `RESULTADO FINAL` é o total do sistema. A planilha da equipe tem um segundo `RESULTADO FINAL` que soma eventos lançados à mão, e ele é **ignorado**, porque eventos estão fora do sistema (ver escopo negativo).
- Export cru tem uma aba. A planilha de acompanhamento da equipe tem uma aba por mês (`SETEMBRO26 25,17`), e o tradutor escolhe a aba do período.

### DRE gerencial de compras

- Cada linha tem um código de conta: `2.01` = CUSTOS, `2.01.01` = grupo (ALIMENTOS), `2.01.01.00002` = subgrupo (BOVINOS).
- `(=) RECEITA LIQUIDA` (sem código) = receita do mês.

## A regra do cálculo

- Entram só os grupos do **CMV direto** — e quais são eles é **deduzido do dado**, não configurado (ver abaixo).
- **CMV % = custo ÷ venda líquida do grupo no cardápio**, com o **mesmo denominador** para teórico e real. Assim a diferença em pontos percentuais é só diferença de custo.
- Sem cardápio no mês, o CMV real usa a receita líquida da DRE.
- **Ajuste = real − teórico**, em R$ e em pontos percentuais.

### Quais grupos formam o CMV direto

Até 05/11/2026 isto era uma constante no código: `GRUPOS_CMV = ("ALIMENTOS",
"BEBIDAS")`. Funcionava para o cliente e inviabilizava qualquer afirmação de que
o sistema serve a outro negócio — uma farmácia não vende "bebidas".

A regra que substituiu a lista não precisa de configuração nenhuma
(`crud.grupos_comparaveis`): **comparável é o grupo que os dois lados do
fechamento reportam.** É exatamente o que separa custo de mercadoria do resto:

| Aparece em | Exemplos | Por que fica fora |
|---|---|---|
| Só na DRE de compras | UTENSILIOS, MATERIAL DE CONSUMO, PRODUTOS REVENDA | Custo indireto, sem baixa de estoque — não há teórico para comparar |
| Só no cardápio | SERVICOS (couvert), OUTRAS VENDAS | Receita sem custo de mercadoria — não há real para comparar |
| Nos dois | ALIMENTOS, BEBIDAS | É o CMV direto |

Na base real do cliente a dedução devolve exatamente `ALIMENTOS` e `BEBIDAS` —
os mesmos números de antes, sem cravar o domínio no código.

O conjunto é **por casa**, não por mês: 23 dos 24 meses de histórico têm só o
cardápio, e exigir os dois relatórios no mesmo mês esvaziaria a série. Os meses
incompletos herdam o conjunto aprendido nos meses completos da mesma casa.

**Limite declarado:** uma casa que nunca enviou cardápio não tem como saber que
"material de consumo" não é mercadoria — nada no arquivo diz isso. Nesse caso o
sistema soma todos os grupos com custo, em vez de aplicar uma taxonomia de
restaurante que não tem como conhecer. Basta um cardápio, de qualquer mês, para
a dedução passar a funcionar.

## Explicação do ajuste (RF11)

> **Entregue e no ar desde 07/11/2026.** Especificação completa,
> com contrato da API e testes, em `11-ciclo-explicacao-do-ajuste.md`, seção 3.
> Regras e texto em `app/services/explicacao.py` (funções puras, sem banco e
> sem LLM); testes em `tests/test_explicacao.py`.

Mostrar o ajuste não basta — o ERP do cliente já tem os números. O fechamento
passa a dizer **onde** a diferença está e **o que conferir**, em texto gerado
por regras (sem LLM), escrito para o sócio:

- **Contribuição de cada grupo em pontos do total**: `ajuste(g) ÷ venda total × 100`. O `ajuste_pp` de cada grupo usa a venda do próprio grupo e não soma ao total; a contribuição soma.
- **Três situações, não duas:** acima do previsto, dentro (±1 pp, premissa declarada) e **abaixo** do previsto. Abaixo não é economia: normalmente falta algo no lado real (compra não lançada, inventário superestimado) ou sobra no teórico (ficha superestimada, período desalinhado). O caso real de set/26 (−3,68 pp) é deste tipo.
- **Compensação declarada:** um grupo acima e outro abaixo podem se anular no total; o texto diz isso.
- **Subgrupos só onde existem nos dois lados.** No Everest, os subgrupos do cardápio são categorias de **venda** (PETISCOS) e os da DRE são categorias de **insumo** (BOVINOS). Não existe "BOVINOS teórico" sem ficha técnica explodida em insumos, que o sistema não recebe. O resto aparece como composição do custo, nunca como desvio — e a tela diz por quê.

## O terceiro formato: planilha genérica

Os dois tradutores acima são do Everest. O terceiro (`ler_planilha`) lê uma
**tabela comum**, que qualquer ERP exporta — é o que sustenta a tese de que
adaptar o sistema a outra origem é escrever um tradutor, não mexer na regra:

| grupo | subgrupo | item | quantidade | venda_liquida | custo |
|---|---|---|---|---|---|
| MEDICAMENTOS | GENERICOS | DIPIRONA 500MG | 820 | 14760 | 5904 |
| PERFUMARIA | HIGIENE | SABONETE 90G | 1900 | 9500 | 4750 |

- Só `grupo` e `custo` são obrigatórios para o arquivo ser aceito: um relatório de compras não tem venda. No lado teórico, porém, sem `venda_liquida` não há CMV % (ver tabela C acima).
- As colunas são localizadas **por nome**, em qualquer ordem, e colunas desconhecidas são ignoradas. Aceita sinônimos (`categoria`, `produto`, `receita`, `faturamento`…).
- A hierarquia é **calculada**: o arquivo traz linhas planas e o tradutor soma subgrupo, grupo e total.
- O **formato é detectado**, não declarado: `leitores.ler` tenta o leitor do Everest e cai no genérico se não reconhecer. O usuário só diz se o arquivo é o lado teórico (`cardapio`) ou o real (`compras`).

Para ver isso rodando num negócio que não é restaurante:

```bash
# todos os ramos de exemplos/ (farmácia, padaria, pizzaria, distribuidora)
uv run python scripts/popular_demo_generico.py --api http://localhost:8000

# só um deles
uv run python scripts/popular_demo_generico.py --empresa padaria-sao-jose

# só gerar os .xlsx, sem tocar a API
uv run python scripts/popular_demo_generico.py --apenas-planilhas pasta/
```

Cria quatro unidades com 6 meses nos dois lados, a partir dos CSVs de
`exemplos/`. O lado real das DEMO é um movimento de estoque por item, e o custo
real sai de **estoque inicial + compras − estoque final** — a mesma regra do
cliente; cada desvio plantado tem causa nomeada em `exemplos/README.md`.
Acrescentar um ramo é acrescentar dois CSVs e uma entrada no
manifesto — **sem tocar Python**.

**O que as DEMO provam, e o que não provam.** Provam que o **formato** e a
**regra** não dependem do Everest nem do ramo. Não provam que existe cliente
nesses ramos, nem que o pequeno negócio tem os dados da seção "O que o usuário
precisa fornecer". E têm uma diferença em relação ao dado real: nelas os
subgrupos são **iguais** nos dois lados, então a comparação por subgrupo do
RF11 parece completa nas DEMO e quase vazia na casa real. Isso é esperado.

**Dado fictício e rotulado "(DEMO)".** As quatro estão em produção; o fechamento
de cada uma, com os grupos que o sistema deduziu, está em `01-requisitos.md` 1.8.
Testes em `tests/test_generalizacao.py`.

## Como importar dados reais localmente

Os arquivos reais têm CNPJ, faturamento e custos do cliente. **Nunca vão para o
GitHub**: ficam em `dados_reais/` (no `.gitignore`, assim como `*.xlsx`). Os
testes usam planilhas sintéticas geradas em `tests/planilhas.py`.

```bash
uv run python scripts/importar_exports.py \
    --casa "Boteco São Bento - Vila Madalena" --tipo cardapio \
    --arquivo "dados_reais/SB VILA CMV CARDAPIO.xlsx" \
    --periodos 2026-07 2026-08 2026-09
```

## Endpoints

| Método | Rota | Para quê |
|---|---|---|
| POST | `/api/v1/uploads-custo` | Envia um export (`casa_id`, `periodo`, `tipo`, `arquivo`). Reenviar o mesmo casa/período/tipo substitui o anterior |
| GET | `/api/v1/metricas/fechamento` | Teórico × real × ajuste por grupo e total |
| GET | `/api/v1/metricas/evolucao` | CMV teórico × real mês a mês |
| GET | `/api/v1/metricas/top-itens` | Itens que mais pesam (`ordem=custo` ou `ordem=cmv`) |
| GET | `/api/v1/modelos/{tipo}` | Planilha-modelo `.xlsx` (`tipo` = `cardapio` \| `compras`) gerada na hora, com linhas sintéticas |

O campo `explicacao` do fechamento (RF11) é **opcional** no contrato: o
frontend em produção continua funcionando entre o deploy do backend e o do
front. Formato em `11-ciclo-explicacao-do-ajuste.md`, seção 3.5.

## Pendências e próximos passos

Atualizado em 06/11/2026: o cliente parou de responder depois da Conversa 2, e
tudo que depende dele está **bloqueado**, não em andamento.

- ⛔ **CMV de compras dos mesmos meses do cardápio** (jul–ago/26, SB Vila), pedido à Marcela em 03/11. Sem resposta.
- ⛔ **Proveniência da DRE recebida em 23/10:** o arquivo **não diz de qual casa nem de qual mês é** — só traz o timestamp do export no nome. O rótulo `2026-09` é uma atribuição de quem rodou o importador, apoiada em evidência circunstancial (exportada em 23/10, logo set/26 é o último mês fechado; a receita da DRE fica a ~1,6% da venda do cardápio do mês). **Não é prova.** Ver `01-requisitos.md` 1.9.
- ⛔ Conferir os números com a apresentação de fechamento de set/26 da equipe (o gabarito nunca chegou).
- **Relatório de inventário e perdas**, para decompor o ajuste em contagem + perdas + não explicado (Should) — depende de arquivo que não temos.
- **Fora do MVP:** alertas durante o mês (divergência de estoque, oscilação de preço, pendências por WhatsApp), recebimento de mercadoria, eventos e buffet, integração via API do Everest.
