"""Casa de demonstração: cardápio REAL do São Bento, estoque SIMULADO.

Desde 18/11/2026 a demonstração é uma casa só, "Boteco Sao Bento -
Demonstracao (DEMO)", para o roteiro ser contínuo. O cardápio por item dela é
copiado da casa piloto real, mês a mês, pela própria API
(`scripts/popular_demo_fechamento.py`) — nenhum dado do cliente fica neste
repositório. Ficam aqui só as regras do que o cliente NÃO tem:

**o estoque e as compras.** Sem inventário não existe CMV real (ver
docs/07-fechamento-cmv.md), então o lado real da demonstração é simulado a
partir do teórico real de cada mês:

    estoque final   = custo teórico × cobertura do grupo (± oscilação do mês)
    consumo         = custo teórico × (1 + quebra normal do grupo)
    compras         = consumo − estoque inicial + estoque final

No último mês (o enviado ao vivo) BEBIDAS tem uma perda de 2,6% da venda e o
estoque de bebidas cai 25%. Resultado: o CMV real fica ACIMA do previsto,
puxado por BEBIDAS, enquanto as COMPRAS do mês ficam ABAIXO do teórico — quem
olhasse só a DRE de compras concluiria o contrário. É exatamente o que
aconteceu com o −3,68 pp real da casa piloto, que é compras sem estoque.

Os meses anteriores ficam dentro da margem de ±1 ponto (só a quebra normal).
"""

CASA_DEMO = {
    "nome": "Boteco Sao Bento - Demonstracao (DEMO)",
    "marca": "Boteco Sao Bento",
    "cidade": "Sao Paulo",
}

CASA_ORIGEM = "Boteco Sao Bento - Vila Madalena"
"""Casa real de onde o script copia o cardápio por item."""

MESES = 13
"""Meses copiados: o mês ao vivo e os 12 anteriores — dá a comparação com o
mesmo mês do ano passado (margem por item) e um ano de evolução."""

COBERTURA = {"ALIMENTOS": 0.30, "BEBIDAS": 0.85}
"""Estoque de fim de mês como fração do custo teórico do mês: perecível gira
rápido, bebida fica parada mais tempo."""
COBERTURA_PADRAO = 0.5

QUEBRA = {"ALIMENTOS": 0.010, "BEBIDAS": 0.006}
"""Quebra normal sobre o custo teórico — fica dentro da margem de ±1 ponto."""
QUEBRA_PADRAO = 0.008

GRUPO_DA_PERDA = "BEBIDAS"
PERDA_AO_VIVO = 0.026
"""Perda plantada no mês ao vivo, como fração da venda do grupo."""
QUEDA_ESTOQUE_AO_VIVO = 0.25
"""Quanto o estoque do grupo da perda cai no mês ao vivo."""


def _oscilacao(periodo: str, grupo: str) -> float:
    """Variação determinística de −6% a +6% no estoque do mês: o mesmo mês dá
    sempre o mesmo número, a cada execução do script."""
    semente = sum((i + 1) * ord(c) for i, c in enumerate(periodo + grupo))
    return (semente % 13 - 6) / 100


def simular(totais: dict[str, dict[str, tuple[float, float]]]) -> list[tuple]:
    """Linhas da planilha de fechamento para TODOS os meses de `totais`.

    `totais[periodo][grupo] = (venda_liquida, custo_teorico)`, somados do
    cardápio da casa. O último mês é o ao vivo. Cada linha: (periodo, grupo,
    venda_liquida, custo_teorico, estoque_inicial, compras, estoque_final),
    com estoque inicial só no primeiro mês de cada grupo — nos outros o
    sistema usa o estoque final do mês anterior.
    """
    periodos = sorted(totais)
    if not periodos:
        return []
    ao_vivo = periodos[-1]
    estoque_anterior: dict[str, float] = {}
    linhas: list[tuple] = []
    for periodo in periodos:
        for grupo in sorted(totais[periodo]):
            venda, teorico = totais[periodo][grupo]
            cobertura = COBERTURA.get(grupo, COBERTURA_PADRAO)
            final = teorico * cobertura * (1 + _oscilacao(periodo, grupo))
            consumo = teorico * (1 + QUEBRA.get(grupo, QUEBRA_PADRAO))
            if periodo == ao_vivo and grupo == GRUPO_DA_PERDA:
                consumo += venda * PERDA_AO_VIVO
                final *= 1 - QUEDA_ESTOQUE_AO_VIVO
            final = round(final, 2)
            primeiro = grupo not in estoque_anterior
            inicial = round(teorico * cobertura, 2) if primeiro else estoque_anterior[grupo]
            compras = round(consumo - inicial + final, 2)
            linhas.append(
                (
                    periodo,
                    grupo,
                    round(venda, 2),
                    round(teorico, 2),
                    inicial if primeiro else None,
                    compras,
                    final,
                )
            )
            estoque_anterior[grupo] = final
    return linhas
