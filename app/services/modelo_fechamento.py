"""Planilha-modelo de fechamento (`GET /api/v1/modelos/fechamento`).

Três abas:
  - Fechamento:  a única que o sistema lê (`leitor_fechamento.py`)
  - Instrucoes:  como preencher
  - Conferencia: fórmulas que refazem a conta, para o usuário conferir antes
                 de enviar. As fórmulas não usam TEXT(), que depende do idioma
                 do Excel — o período anterior é montado com LEFT/RIGHT.

Os valores de exemplo são sintéticos (regra do repositório: nenhum número do
cliente sai daqui). Foram escolhidos para mostrar por que o estoque é
obrigatório: em 2026-09 as compras de BEBIDAS ficam abaixo do teórico, mas o
estoque caiu e o consumo real fica acima.
"""

import io

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.worksheet.datavalidation import DataValidation

LINHAS_PREPARADAS = 300
"""Linhas da aba Fechamento com validação e da aba Conferencia com fórmula."""

COLUNAS = [
    # nome, largura, obrigatória
    ("periodo", 11, True),
    ("grupo", 18, True),
    ("venda_liquida", 16, True),
    ("custo_teorico", 16, False),
    ("estoque_inicial", 16, False),
    ("compras", 16, True),
    ("estoque_final", 16, True),
]

EXEMPLO = [
    ("2026-07", "ALIMENTOS", 250000, 67500, 40000, 70000, 42000),
    ("2026-07", "BEBIDAS", 300000, 75000, 100000, 72000, 95000),
    ("2026-08", "ALIMENTOS", 270000, 72900, None, 78000, 44000),
    ("2026-08", "BEBIDAS", 320000, 80000, None, 90000, 104000),
    ("2026-09", "ALIMENTOS", 240000, 64800, None, 60000, 39000),
    ("2026-09", "BEBIDAS", 290000, 72500, None, 65000, 94000),
]

INSTRUCOES = [
    ("Planilha-modelo · Fechamento de CMV", None, None, "titulo"),
    (
        "Preencha só a aba Fechamento. Uma linha por grupo por mês. "
        "A aba Conferencia refaz a conta para você conferir.",
        None,
        None,
        "nota",
    ),
    (None, None, None, None),
    ("A conta", None, None, "secao"),
    ("CMV real", "", "estoque inicial + compras − estoque final", None),
    ("CMV %", "", "CMV real ÷ venda líquida", None),
    ("Ajuste", "", "CMV real − custo teórico (em R$ e em pontos percentuais)", None),
    (None, None, None, None),
    ("Colunas", "Obrigatória?", "O que informar", "secao"),
    ("periodo", "Sim", "Mês no formato AAAA-MM (ex.: 2026-09).", None),
    (
        "grupo",
        "Sim",
        "Grupo de custo direto (ex.: ALIMENTOS, BEBIDAS). Use sempre o mesmo nome em "
        "todos os meses. Não inclua custos indiretos (utensílios, material de limpeza, "
        "embalagens de uso interno).",
        None,
    ),
    (
        "venda_liquida",
        "Sim",
        "Venda líquida do grupo no mês (sem descontos, cancelamentos e taxa de serviço).",
        None,
    ),
    (
        "custo_teorico",
        "Não",
        "Custo previsto pelas fichas técnicas: soma de (quantidade vendida × custo da "
        "ficha). Sem ela, o sistema mostra o CMV real, mas não o ajuste.",
        None,
    ),
    (
        "estoque_inicial",
        "Só no 1º mês",
        "Valor do estoque do grupo no início do mês. Depois do primeiro mês, deixe em "
        "branco: o sistema usa o estoque_final do mês anterior. Se preencher, o valor "
        "informado vale.",
        None,
    ),
    (
        "compras",
        "Sim",
        "Compras do grupo no mês, já líquidas: descontando devoluções e transferências "
        "para outras unidades. Bonificação (mercadoria recebida sem custo) não entra.",
        None,
    ),
    (
        "estoque_final",
        "Sim",
        "Valor do estoque do grupo no inventário do último dia do mês. Sem inventário "
        "não há CMV real: o mês é recusado.",
        None,
    ),
    (None, None, None, None),
    ("Regras", None, None, "secao"),
    (
        "1",
        "",
        "Valores em reais, sem R$, maiores ou iguais a zero. Vírgula ou ponto decimal são aceitos.",
        None,
    ),
    ("2", "", "Um grupo aparece uma vez por mês. Grupo repetido no mesmo mês é erro.", None),
    (
        "3",
        "",
        "Pode enviar um mês ou vários de uma vez (histórico). Reenviar um mês substitui "
        "o anterior.",
        None,
    ),
    ("4", "", "Uma unidade (loja/casa) por arquivo.", None),
    (
        "5",
        "",
        "Primeiro mês de um grupo sem estoque_inicial é erro: não há de onde tirar o "
        "estoque de abertura.",
        None,
    ),
    (
        "6",
        "",
        "Estoque inicial e final são o mesmo inventário visto de dois lados: o final de "
        "um mês é o inicial do seguinte. Conte sempre no mesmo dia e com o mesmo "
        "critério de valor (custo médio).",
        None,
    ),
    (None, None, None, None),
    ("Por que o estoque é obrigatório", None, None, "secao"),
    (
        "",
        "",
        "Compras não é consumo. No exemplo, em 2026-09 as compras de BEBIDAS (65.000) "
        "ficam abaixo do teórico (72.500), mas o estoque caiu 10.000: o consumo real foi "
        "75.000, acima do teórico. Olhando só compras, a conclusão sairia invertida.",
        None,
    ),
    (None, None, None, None),
    (
        "Os valores de exemplo são fictícios. Apague as linhas de exemplo antes de preencher.",
        None,
        None,
        "nota",
    ),
]

_AZUL = PatternFill("solid", fgColor="1F4E78")
_OPCIONAL = PatternFill("solid", fgColor="5B7DA6")
_CALC = PatternFill("solid", fgColor="375623")
_BRANCO = Font(bold=True, color="FFFFFF")
_FINA = Side(style="thin", color="BFBFBF")
_BORDA = Border(left=_FINA, right=_FINA, top=_FINA, bottom=_FINA)
_MOEDA = "#,##0.00"
_PCT = "0.00%"
_PP = '+0.00" pp";-0.00" pp";0.00" pp"'


def gerar_modelo_fechamento() -> bytes:
    """Monta o `.xlsx` em memória. Função pura: nada de disco, nada de banco."""
    livro = Workbook()
    _aba_fechamento(livro.active)
    _aba_instrucoes(livro.create_sheet("Instrucoes"))
    _aba_conferencia(livro.create_sheet("Conferencia"))
    buffer = io.BytesIO()
    livro.save(buffer)
    return buffer.getvalue()


def _cabecalho(aba, titulos: list[tuple[str, int, PatternFill]]) -> None:
    for i, (nome, largura, cor) in enumerate(titulos, start=1):
        c = aba.cell(row=1, column=i, value=nome)
        c.font = _BRANCO
        c.fill = cor
        c.alignment = Alignment(horizontal="center")
        c.border = _BORDA
        aba.column_dimensions[c.column_letter].width = largura
    aba.freeze_panes = "A2"


def _aba_fechamento(aba) -> None:
    aba.title = "Fechamento"
    _cabecalho(aba, [(n, w, _AZUL if obrig else _OPCIONAL) for n, w, obrig in COLUNAS])
    for r, linha in enumerate(EXEMPLO, start=2):
        for i, valor in enumerate(linha, start=1):
            c = aba.cell(row=r, column=i, value=valor)
            c.border = _BORDA
            if i >= 3:
                c.number_format = _MOEDA
    # período como texto, para o Excel não converter "2026-07" em data
    for r in range(2, LINHAS_PREPARADAS + 2):
        aba.cell(row=r, column=1).number_format = "@"

    ultima = LINHAS_PREPARADAS + 1
    periodo = DataValidation(
        type="textLength",
        operator="equal",
        formula1="7",
        allow_blank=True,
        showErrorMessage=True,
        errorTitle="Período inválido",
        error="Use o formato AAAA-MM, por exemplo 2026-09.",
    )
    valor = DataValidation(
        type="decimal",
        operator="greaterThanOrEqual",
        formula1="0",
        allow_blank=True,
        showErrorMessage=True,
        errorTitle="Valor inválido",
        error="Informe um número maior ou igual a zero, sem R$.",
    )
    aba.add_data_validation(periodo)
    aba.add_data_validation(valor)
    periodo.add(f"A2:A{ultima}")
    valor.add(f"C2:G{ultima}")


def _aba_instrucoes(aba) -> None:
    aba.column_dimensions["A"].width = 20
    aba.column_dimensions["B"].width = 16
    aba.column_dimensions["C"].width = 90
    for r, (a, b, c, estilo) in enumerate(INSTRUCOES, start=1):
        for col, v in enumerate((a, b, c), start=1):
            aba.cell(row=r, column=col, value=v).alignment = Alignment(
                wrap_text=True, vertical="top"
            )
        if estilo == "titulo":
            aba.cell(row=r, column=1).font = Font(bold=True, size=14, color="1F4E78")
        elif estilo == "secao":
            for col in range(1, 4):
                aba.cell(row=r, column=col).font = _BRANCO
                aba.cell(row=r, column=col).fill = _AZUL
        elif estilo == "nota":
            aba.cell(row=r, column=1).font = Font(italic=True, color="595959")
            aba.merge_cells(start_row=r, start_column=1, end_row=r, end_column=3)
        elif a:
            aba.cell(row=r, column=1).font = Font(bold=True)


def _aba_conferencia(aba) -> None:
    _cabecalho(
        aba,
        [
            ("periodo", 11, _CALC),
            ("grupo", 18, _CALC),
            ("estoque_inicial usado", 20, _CALC),
            ("CMV real", 16, _CALC),
            ("CMV real %", 12, _CALC),
            ("CMV teórico %", 14, _CALC),
            ("ajuste R$", 14, _CALC),
            ("ajuste pp", 12, _CALC),
            ("aviso", 46, _CALC),
        ],
    )
    f = "Fechamento!"
    for r in range(2, LINHAS_PREPARADAS + 2):
        vazio = f'{f}A{r}=""'
        ano = f"VALUE(LEFT({f}A{r},4))"
        mes = f"VALUE(RIGHT({f}A{r},2))"
        anterior = f'IF({mes}=1,({ano}-1)&"-12",{ano}&"-"&IF({mes}-1<10,"0","")&({mes}-1))'
        ef_anterior = f"SUMIFS({f}$G:$G,{f}$B:$B,{f}B{r},{f}$A:$A,{anterior})"
        tem_anterior = f"COUNTIFS({f}$B:$B,{f}B{r},{f}$A:$A,{anterior})>0"
        ei = f'IF({f}E{r}<>"",{f}E{r},IF({tem_anterior},{ef_anterior},""))'
        aviso = (
            f'=IF({vazio},"",'
            f'IF(COUNTIFS({f}$A:$A,{f}A{r},{f}$B:$B,{f}B{r})>1,"Grupo repetido neste mês",'
            f'IF(C{r}="","Falta estoque_inicial (primeiro mês do grupo)",'
            f'IF({f}G{r}="","Falta estoque_final: sem inventário não há CMV real",'
            f'IF({f}D{r}="","Sem custo_teorico: só CMV real, sem ajuste","")))))'
        )
        formulas = [
            f'=IF({vazio},"",{f}A{r})',
            f'=IF({vazio},"",{f}B{r})',
            f'=IF({vazio},"",{ei})',
            f'=IF(OR({vazio},C{r}="",{f}G{r}=""),"",C{r}+{f}F{r}-{f}G{r})',
            f'=IF(OR(D{r}="",N({f}C{r})=0),"",D{r}/{f}C{r})',
            f'=IF(OR({vazio},{f}D{r}="",N({f}C{r})=0),"",{f}D{r}/{f}C{r})',
            f'=IF(OR(D{r}="",{f}D{r}=""),"",D{r}-{f}D{r})',
            f'=IF(OR(E{r}="",F{r}=""),"",(E{r}-F{r})*100)',
            aviso,
        ]
        for col, formula in enumerate(formulas, start=1):
            aba.cell(row=r, column=col, value=formula)
        for col, fmt in ((3, _MOEDA), (4, _MOEDA), (5, _PCT), (6, _PCT), (7, _MOEDA), (8, _PP)):
            aba.cell(row=r, column=col).number_format = fmt
