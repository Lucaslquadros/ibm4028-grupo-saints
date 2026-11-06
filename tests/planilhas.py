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


# ------------------------------------------- planilha genérica (outro domínio)
# De propósito NÃO é um restaurante: o objetivo é provar que o fechamento não
# depende de ALIMENTOS/BEBIDAS nem do Everest. Aqui é uma farmácia.
#
#   teórico  MEDICAMENTOS venda 1500 custo  650 → 43,33%
#            PERFUMARIA   venda  600 custo  300 → 50,00%
#            TOTAL        venda 2100 custo  950 → 45,24%
#   real     MEDICAMENTOS custo 700 → 46,67% (+3,34 pp)
#            PERFUMARIA   custo 320 → 53,33% (+3,33 pp)
#            EMBALAGENS   custo 150 → só no lado real, fica FORA do CMV direto
#            TOTAL        custo 1020 → 48,57% (+3,33 pp), ajuste +70


def linhas_planilha_teorico() -> list[list]:
    # Ordem das colunas trocada e uma coluna extra desconhecida, para provar que
    # o leitor acha as colunas pelo NOME e tolera o que não conhece.
    return [
        ["Custo", "Item", "Grupo", "Subgrupo", "Quantidade", "Venda Líquida", "Observação"],
        [400, "DIPIRONA 500MG", "MEDICAMENTOS", "GENERICOS", 100, 1000, "ignorar"],
        [250, "AMOXICILINA", "MEDICAMENTOS", "GENERICOS", 50, 500, None],
        [300, "SABONETE", "PERFUMARIA", "HIGIENE", 200, 600, None],
        [],
    ]


def linhas_planilha_real() -> list[list]:
    # Sem coluna de venda: um relatório de compras não tem receita. Só 'grupo' e
    # 'custo' são obrigatórios.
    return [
        ["Grupo", "Subgrupo", "Custo"],
        ["MEDICAMENTOS", "GENERICOS", 700],
        ["PERFUMARIA", "HIGIENE", 320],
        ["EMBALAGENS", "DESCARTAVEIS", 150],
    ]


def planilha_teorico_xlsx() -> bytes:
    return xlsx({"Dados": linhas_planilha_teorico()})


def planilha_item_xlsx(
    *, nome: str = "BOLINHO", grupo: str = "ALIMENTOS", quantidade: float, custo: float = 200.0
) -> bytes:
    """Planilha genérica de um item só, com a **quantidade** sob controle.

    Existe porque o `fator` de `cardapio_xlsx` escala dinheiro (venda e custo),
    não quantidade — BOLINHO vende 10 unidades em qualquer fator. Para testar
    previsão de demanda, que lê justamente a quantidade, é preciso variá-la de
    mês a mês, e é o que esta função permite.
    """
    return xlsx(
        {
            "Dados": [
                ["Grupo", "Subgrupo", "Item", "Quantidade", "Venda Líquida", "Custo"],
                [grupo, "GERAL", nome, quantidade, quantidade * 60, custo],
            ]
        }
    )


def planilha_real_xlsx() -> bytes:
    return xlsx({"Dados": linhas_planilha_real()})


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
