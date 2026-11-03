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

- Entram só os grupos do **CMV direto**: `ALIMENTOS` e `BEBIDAS`. A DRE tem também utensílios e material de consumo (custo indireto, sem baixa), e o cardápio tem serviços (couvert, sem custo de mercadoria).
- **CMV % = custo ÷ venda líquida do grupo no cardápio**, com o **mesmo denominador** para teórico e real. Assim a diferença em pontos percentuais é só diferença de custo.
- Sem cardápio no mês, o CMV real usa a receita líquida da DRE.
- **Ajuste = real − teórico**, em R$ e em pontos percentuais.

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

## Pendências e próximos passos

- **CMV de compras dos mesmos meses do cardápio** (jul–set/26, SB Vila), pedido à Marcela. A DRE recebida em 23/10 não diz de qual casa e mês é.
- **Relatório de inventário e perdas**, para decompor o ajuste em contagem + perdas + não explicado (Should).
- Conferir os números com a apresentação de fechamento de set/26 da equipe (o gabarito).
- **Fora do MVP:** alertas durante o mês (divergência de estoque, oscilação de preço, pendências por WhatsApp), recebimento de mercadoria, eventos e buffet, integração via API do Everest.
