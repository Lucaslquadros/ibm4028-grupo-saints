"""Planilhas SINTÉTICAS no layout dos exports do Everest, geradas em memória.

Os testes nunca usam os arquivos reais do cliente (CNPJ, faturamento, custos):
aqui reproduzimos só a ESTRUTURA — cabeçalho, grupos, subgrupos, itens e o
bloco de RESULTADO FINAL — com números inventados e fáceis de conferir.

Números do cardápio sintético (período de teste):
  ALIMENTOS  venda 1000  custo 300  (PETISCOS: BOLINHO 600/200, PASTEL 400/100)
  BEBIDAS    venda 2000  custo 400  (CHOPP: CHOPP 300ML 2000/400)
  SERVICOS   venda  100  custo   0
Números da DRE sintética:
  receita 3200 | ALIMENTOS 330 (BOVINOS 200, HORTIFRUTI 130) | BEBIDAS 420
  | MATERIAL DE CONSUMO 250 (custo indireto, fora do CMV direto)
"""

import io

from openpyxl import Workbook

TITULOS_CARDAPIO = [
    None, None, "% Represen", "Q. Venda", "Preço médio", "V. Venda Bruta",
    "V. Desconto", "% desc", "V. Venda Líquida", "Custo Unitario ", "Custo Geral ",
    "CMV Bruto ", "Cmv  Liquido", "Variação",
]  # fmt: skip


def _linha(col_a, col_b, qtd, venda, custo) -> list:
    return [col_a, col_b, None, qtd, None, venda, 0, 0, venda, None, custo, None, None, None]


def _bloco_resultado(venda, custo) -> list[list]:
    titulos = [
        None, "RESULTADO FINAL ", None, None, "V. Venda Bruta", "V. Desconto",
        "% desc", "V. Venda Líquida", "Custo Geral ", "CMV Bruto ", "CMV  Liquido",
    ]  # fmt: skip
    valores = [None, None, None, None, venda, 0, 0, venda, custo, None, None]
    return [titulos, valores]


def linhas_cardapio(fator: float = 1.0) -> list[list]:
    f = fator
    linhas = [
        TITULOS_CARDAPIO,
        _linha("ALIMENTOS", None, 15, 1000 * f, 300 * f),
        _linha("PETISCOS", None, 15, 1000 * f, 300 * f),
        _linha(None, "BOLINHO", 10, 600 * f, 200 * f),
        _linha(None, "PASTEL", 5, 400 * f, 100 * f),
        _linha("BEBIDAS", None, 100, 2000 * f, 400 * f),
        _linha("CHOPP", None, 100, 2000 * f, 400 * f),
        _linha(None, "CHOPP 300ML", 100, 2000 * f, 400 * f),
        _linha("SERVICOS", None, 10, 100 * f, 0),
        _linha("OUTROS", None, 10, 100 * f, 0),
        _linha(None, "COUVERT", 10, 100 * f, 0),
        [],
        *_bloco_resultado(3100 * f, 700 * f),
        [],
        # bloco de eventos lançado à mão pela equipe: deve ser IGNORADO
        [None, "TOTAL GERAL EVENTO", None, "Representatividade", "V. Venda Bruta"],
        [None, None, None, 0.1, 999],
        *_bloco_resultado(9999, 9999),
    ]
    return linhas


def linhas_dre() -> list[list]:
    return [
        [None, "(=) RECEITA LIQUIDA", 3200, 100, 3200],
        [None, "(-) CUSTOS", 1000, 31.25, 1000],
        ["2", "    CUSTOS E DESPESAS", 1000, 31.25, 1000],
        ["2.01", "        CUSTOS", 1000, 31.25, 1000],
        ["2.01.01", "            ALIMENTOS", 330, 10.3, 330],
        ["2.01.01.00001", "                BOVINOS", 200, 6.25, 200],
        ["2.01.01.00002", "                HORTIFRUTI", 130, 4.06, 130],
        ["2.01.02", "            BEBIDAS", 420, 13.1, 420],
        ["2.01.02.00003", "                CHOPP", 420, 13.1, 420],
        ["2.01.04", "            MATERIAL DE CONSUMO", 250, 7.8, 250],
        ["2.01.04.00003", "                DESCARTAVEIS", 250, 7.8, 250],
    ]


def xlsx(abas: dict[str, list[list]]) -> bytes:
    """{nome_da_aba: linhas} → bytes de um .xlsx."""
    livro = Workbook()
    livro.remove(livro.active)
    for nome, linhas in abas.items():
        aba = livro.create_sheet(nome)
        for linha in linhas:
            aba.append(linha)
    buffer = io.BytesIO()
    livro.save(buffer)
    return buffer.getvalue()


def cardapio_xlsx(fator: float = 1.0) -> bytes:
    return xlsx({"Página 1": linhas_cardapio(fator)})


def dre_xlsx() -> bytes:
    return xlsx({"DRE Gerencial": linhas_dre()})
