"""Cardápio SINTÉTICO por item para os testes — números inventados.

Era o cardápio da antiga casa de demonstração fictícia (até 18/11/2026). A demo
passou a usar o cardápio real do São Bento, copiado pela API por
`scripts/popular_demo_fechamento.py`, e este conjunto ficou só para os testes:
seis meses (abr–set/26), ALIMENTOS e BEBIDAS, com três itens de custo subindo
(margem por item) e item nos quatro quadrantes (engenharia de cardápio).
"""

import io

from openpyxl import Workbook

# periodo, grupo, venda_liquida, custo_teorico, estoque_inicial, compras, estoque_final
LINHAS = [  # só venda e custo teórico importam aqui
    ("2026-04", "ALIMENTOS", 240000, 64800, 40000, 67760, 42000),
    ("2026-04", "BEBIDAS", 290000, 72500, 100000, 68950, 95000),
    ("2026-05", "ALIMENTOS", 255000, 68340, None, 68105, 41000),
    ("2026-05", "BEBIDAS", 305000, 76555, None, 80775, 98000),
    ("2026-06", "ALIMENTOS", 230000, 62560, None, 66210, 43500),
    ("2026-06", "BEBIDAS", 280000, 69720, None, 75120, 102000),
    ("2026-07", "ALIMENTOS", 250000, 67500, None, 67000, 42000),
    ("2026-07", "BEBIDAS", 300000, 75000, None, 71800, 97000),
    ("2026-08", "ALIMENTOS", 270000, 72630, None, 75710, 44000),
    ("2026-08", "BEBIDAS", 320000, 80000, None, 88600, 104000),
    ("2026-09", "ALIMENTOS", 245000, 66150, None, 61130, 38000),
    ("2026-09", "BEBIDAS", 300000, 75000, None, 70800, 92000),
]

PERIODOS = sorted({linha[0] for linha in LINHAS})


def linhas_demo(periodos: list[str]) -> list[tuple]:
    pedidos = set(periodos)
    return [linha for linha in LINHAS if linha[0] in pedidos]


# grupo, subgrupo, item, preço de venda, CMV da ficha, peso na venda do grupo,
# variação do peso por mês (tendência: o RF07 tem o que mostrar), variação do
# CMV da ficha por mês (margem por item: o custo do insumo sobe, o preço não).
#
# Os três itens com custo subindo — GIN TONICA, REFRIGERANTE LATA e PICANHA NA
# CHAPA — são o ponto da tela "Margem por item": o CMV de BEBIDAS na planilha é
# 25% todo mês, e dentro dele gin e refrigerante perdem margem enquanto o chopp
# compensa. Como o custo do grupo é fixo (vem da planilha), os outros itens do
# grupo ficam um pouco mais baratos: a categoria esconde o item.
#
# CALDO DE FEIJAO e LIMONADA JARRA vendem pouco e deixam pouca margem: são os
# "cães" da engenharia de cardápio. A limonada custa MAIS do que é vendida (CMV
# da ficha acima de 100%), como a jarra de limão da casa piloto em set/26 — é o
# item vendido abaixo do custo que a tela destaca.
ITENS = [
    ("ALIMENTOS", "PETISCOS", "BOLINHO DE BACALHAU", 42.0, 0.30, 0.24, 0.00, 0.0),
    ("ALIMENTOS", "PETISCOS", "PASTEL DE CARNE", 28.0, 0.22, 0.18, -0.04, 0.0),
    ("ALIMENTOS", "PETISCOS", "MANDIOCA FRITA", 26.0, 0.18, 0.14, 0.02, 0.0),
    ("ALIMENTOS", "PRATOS", "FILE COM FRITAS", 89.0, 0.33, 0.26, 0.01, 0.0),
    ("ALIMENTOS", "PRATOS", "PICANHA NA CHAPA", 119.0, 0.31, 0.18, 0.03, 0.012),
    ("ALIMENTOS", "PETISCOS", "CALDO DE FEIJAO", 16.0, 0.35, 0.03, 0.0, 0.0),
    ("BEBIDAS", "CHOPP", "CHOPP 300ML", 14.0, 0.24, 0.34, 0.00, 0.0),
    ("BEBIDAS", "CHOPP", "CHOPP 500ML", 21.0, 0.23, 0.22, 0.02, 0.0),
    ("BEBIDAS", "DESTILADOS", "CAIPIRINHA", 28.0, 0.28, 0.20, -0.02, 0.0),
    ("BEBIDAS", "DESTILADOS", "GIN TONICA", 36.0, 0.30, 0.12, 0.05, 0.016),
    ("BEBIDAS", "NAO ALCOOLICOS", "REFRIGERANTE LATA", 8.0, 0.30, 0.12, 0.00, 0.02),
    ("BEBIDAS", "NAO ALCOOLICOS", "LIMONADA JARRA", 18.0, 1.45, 0.02, 0.0, 0.0),
]

CABECALHO_CARDAPIO = ["grupo", "subgrupo", "item", "quantidade", "venda_liquida", "custo"]


def cardapio(periodo: str) -> list[tuple]:
    """Engenharia de cardápio da demo no mês: (grupo, subgrupo, item,
    quantidade, venda_liquida, custo). Os totais por grupo são os da planilha."""
    if periodo not in PERIODOS:
        raise ValueError(f"O conjunto sintético não tem o mês {periodo}")
    indice = PERIODOS.index(periodo)
    linhas: list[tuple] = []
    for _periodo, grupo, venda_grupo, teorico_grupo, *_resto in linhas_demo([periodo]):
        itens = [i for i in ITENS if i[0] == grupo]
        pesos = [peso * (1 + tendencia) ** indice for *_x, peso, tendencia, _d in itens]
        vendas = _repartir(venda_grupo, pesos)
        brutos = [
            v * (cmv + deriva * indice)
            for v, (*_x, cmv, _p, _t, deriva) in zip(vendas, itens, strict=True)
        ]
        custos = _repartir(teorico_grupo, brutos)
        for (_g, subgrupo, item, preco, *_x), venda, custo in zip(
            itens, vendas, custos, strict=True
        ):
            linhas.append((grupo, subgrupo, item, round(venda / preco), venda, custo))
    return linhas


def _repartir(total: float, pesos: list[float]) -> list[float]:
    """`total` dividido na proporção de `pesos`, em centavos, somando exato:
    o arredondamento que sobra vai para o último."""
    soma = sum(pesos)
    partes = [round(total * p / soma, 2) for p in pesos[:-1]]
    return [*partes, round(total - sum(partes), 2)]


def cardapio_xlsx(periodo: str) -> bytes:
    """O cardápio do mês como planilha genérica, pronto para `POST /uploads-custo`."""
    livro = Workbook()
    aba = livro.active
    aba.append(CABECALHO_CARDAPIO)
    for linha in cardapio(periodo):
        aba.append(list(linha))
    buffer = io.BytesIO()
    livro.save(buffer)
    return buffer.getvalue()
