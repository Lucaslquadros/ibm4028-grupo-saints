# Exemplos (DEMO) — quatro negócios fictícios, abr a set/2026

Dados **inventados** para mostrar o fechamento de CMV fora do Grupo Saints.
Carregados por `scripts/popular_demo_generico.py`, que transforma cada mês
num `.xlsx` de planilha genérica e envia pela API.

## Formato

Cada empresa tem dois arquivos, ambos com a coluna `periodo` (`AAAA-MM`):

| Arquivo | Colunas | O que é |
|---|---|---|
| `<slug>-teorico.csv` | grupo, subgrupo, item, quantidade, venda_liquida, custo | Vendas do mês × custo da ficha técnica (lado teórico) |
| `<slug>-real.csv` | grupo, subgrupo, item, estoque_inicial, compras, estoque_final | Movimento de estoque do mês, a custo (lado real) |

O custo real de cada item segue a regra do cliente:

> **custo real = estoque inicial + compras − estoque final**

O script confere que o estoque inicial de cada mês é o estoque final do mês
anterior e manda as três colunas no `.xlsx`, junto com o `custo` calculado, para
quem abrir o arquivo poder conferir a conta. Linhas que só existem no lado real
(EMBALAGENS, MATERIAL DE LIMPEZA, DESCARTAVEIS, LOGISTICA) são custo indireto,
com estoque zero, e o sistema as exclui sozinho do CMV.

As vendas variam mês a mês (sazonalidade do ramo + ruído por item), o que dá
série para a recomendação de compra (RF07). Toda empresa tem uma quebra normal
pequena (0,3% a 1%), por isso os meses sem ocorrência ficam **dentro** da margem
de ±1 pp.

## Desvios plantados (o que o fechamento deve encontrar)

Cada desvio tem causa nomeada, como num fechamento real. Nada de multiplicador
uniforme: se o RF11 apontar outro grupo, alguma coisa está errada.

### Drogaria Central (farmácia)

| Mês | Item | Ocorrência | Efeito no fechamento |
|---|---|---|---|
| jun | SHAMPOO 350ML | Contagem do inventário R$ 1.800 acima do real | jun **abaixo** (−1,76 pp); jul acima, porque o erro volta com sinal trocado |
| ago → | LOSARTANA 50MG | Fornecedor reajustou 12%, custo do cadastro não foi atualizado | MEDICAMENTOS acima a partir de ago |
| ago, set | FRALDA M 30UN | Furto/avaria: R$ 1.400 e R$ 2.600 | PERFUMARIA › INFANTIL concentra o desvio de set |
| set | AMOXICILINA 500MG | Compra de R$ 1.500 não lançada | MEDICAMENTOS › GENERICOS abaixo em set |

**set/26:** +2,66 pp, puxado por PERFUMARIA (fralda).

### Padaria São José

| Mês | Item | Ocorrência | Efeito |
|---|---|---|---|
| todos | PAO FRANCES KG | Sobra de pão não lançada como perda: 3%/mês, 7% em set | PANIFICACAO sempre um pouco acima |
| jul → | QUEIJO MINAS KG | Reajuste de 15%, ficha técnica desatualizada | FRIOS acima a partir de jul |
| set | SONHO | Contagem R$ 900 acima do real | CONFEITARIA abaixo em set: **compensa** parte de FRIOS |

**set/26:** +1,39 pp, puxado por FRIOS (queijo), com compensação de CONFEITARIA.

### Pizzaria Bella

| Mês | Item | Ocorrência | Efeito |
|---|---|---|---|
| mai | PIZZA CALABRESA G | Contagem R$ 700 acima do real | mai abaixo, jun acima |
| ago, set | CERVEJA LONG NECK | Desvio: R$ 400 e R$ 1.300 | BEBIDAS acima |
| set | PIZZA MUSSARELA G | Compra de mussarela (R$ 2.200) não lançada | PIZZAS abaixo |

**set/26:** −0,80 pp no total, **dentro** da margem, mas com BEBIDAS +5,6 pp e
PIZZAS −3,7 pp por grupo. É o caso que mostra por que olhar só o total engana.

### Distribuidora Horizonte (atacado de bebidas)

| Mês | Item | Ocorrência | Efeito |
|---|---|---|---|
| jun → | ENERGETICO 269ML | Reajuste de 8%, custo do cadastro desatualizado | NAO ALCOOLICOS acima a partir de jun |
| ago | WHISKY 12 ANOS | Contagem R$ 1.500 acima do real | DESTILADOS abaixo em ago, acima em set |
| set | CERVEJA PILSEN CX 12 | Palete avariado: R$ 3.800 | CERVEJAS › PILSEN concentra o desvio de set |

**set/26:** +3,49 pp, puxado por CERVEJAS (avaria).

## Como acrescentar um ramo

Dois CSVs neste formato e uma entrada em `empresas.json`, **sem tocar Python**.
Cuide para o estoque inicial de cada mês ser o estoque final do anterior: o
script recusa o arquivo se não for.
