"""Casa de demonstração do fechamento pela planilha-modelo.

Dados **inventados**, rotulados como tal no nome da casa. Servem à
apresentação: o histórico (abr–ago/26) é carregado antes por
`scripts/popular_demo_fechamento.py`, e o último mês (set/26) é enviado ao
vivo, com a planilha que a própria tela de Upload oferece para baixar
(`GET /api/v1/modelos/fechamento/demo/planilha`). Os dois saem desta tabela,
então o estoque inicial em branco de set/26 sempre encontra o estoque final de
ago/26 que o script carregou.

Como os números foram montados (para conferir à mão):

    teórico   = venda × CMV da ficha (≈27% ALIMENTOS, ≈25% BEBIDAS)
    consumo   = teórico + quebra normal (0,3–0,6% da venda)
    compras   = consumo − estoque inicial + estoque final

    abr–ago   ajuste total de +0,35 a +0,51 pp → "dentro" (margem de ±1 pp)
    set/26    perda de chopp: BEBIDAS consome 2,6% da venda acima do teórico.
              Ajuste total +1,61 pp → "acima", puxado por BEBIDAS.
              E o estoque de BEBIDAS caiu 12.000: as **compras** do mês
              (70.800) ficam ABAIXO do teórico (75.000). Quem olhasse só a
              DRE de compras concluiria o contrário — é o ponto da demo.
"""

CASA_DEMO = {
    "nome": "Boteco Exemplo - Pinheiros (DEMO)",
    "marca": "Boteco Exemplo",
    "cidade": "Sao Paulo",
}

PERIODO_AO_VIVO = "2026-09"
"""O mês que fica de fora da carga e é enviado durante a apresentação."""

# periodo, grupo, venda_liquida, custo_teorico, estoque_inicial, compras, estoque_final
LINHAS = [
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
PERIODOS_HISTORICO = [p for p in PERIODOS if p < PERIODO_AO_VIVO]


def linhas_demo(periodos: list[str]) -> list[tuple]:
    """As linhas dos meses pedidos, na ordem da tabela."""
    pedidos = set(periodos)
    return [linha for linha in LINHAS if linha[0] in pedidos]
