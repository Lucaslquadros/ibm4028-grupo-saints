"""Engenharia de cardápio — a matriz popularidade × margem (RF16).

O método é o de Kasavana & Smith (1982), o padrão da gestão de restaurantes, e
dá nome ao relatório que o cliente já exporta do Everest. Cada item vendido no
mês cai num de quatro quadrantes, e cada quadrante tem uma ação conhecida:

    popular + margem alta   ESTRELA          manter e proteger
    popular + margem baixa  BURRO DE CARGA   reajustar preço ou porção
    pouco   + margem alta   QUEBRA-CABEÇA    promover, reposicionar no cardápio
    pouco   + margem baixa  CÃO              reformular ou tirar

Os dois cortes, dentro de cada grupo (ALIMENTOS com ALIMENTOS, BEBIDAS com
BEBIDAS — comparar chopp com picanha não diz nada):

- **margem** = margem de contribuição por unidade (preço − custo da ficha). O
  corte é a média PONDERADA do grupo: margem total ÷ unidades vendidas;
- **popularidade** = fatia das unidades do grupo. O corte é a regra dos 70%:
  um item é popular se vende pelo menos 70% da fatia que teria se todos os N
  itens vendessem igual (0,7 ÷ N).

Por que esta tela e não uma previsão: usa só o que aconteceu (venda e custo da
ficha de cada item), não estima o futuro. "Quanto comprar" (RF07) foi tirado
do menu em 18/11 porque, testado contra o histórico, não previa melhor que
repetir o mês passado — ver docs/01-requisitos.md.

Funções puras: a consulta (GROUP BY por item) é a mesma da margem por item.
"""

from dataclasses import dataclass

from app.services.margem import ItemMes

FATOR_POPULARIDADE = 0.7
"""A regra dos 70% de Kasavana & Smith."""

VENDA_MINIMA = 500.0
"""Item com venda abaixo disso no mês fica fora da MATRIZ (mesma régua da margem
por item). Sem ele, os 243 itens de BEBIDAS da casa piloto — muitos uma garrafa
vendida uma vez — derrubam o corte de popularidade para 0,3% e jogam dois
terços do cardápio em "quebra-cabeça". Esses itens continuam contando para o
alerta de abaixo do custo, que é sobre dinheiro perdido, não sobre volume."""

PRECO_SIMBOLICO = 1.0
"""Preço médio abaixo disso é cortesia lançada com valor simbólico (porção de
arroz a R$ 0,01): custo maior que o preço ali não é prejuízo de cardápio."""

ESTRELA = "estrela"
BURRO_DE_CARGA = "burro_de_carga"
QUEBRA_CABECA = "quebra_cabeca"
CAO = "cao"
CLASSES = (ESTRELA, BURRO_DE_CARGA, QUEBRA_CABECA, CAO)


@dataclass(frozen=True)
class Corte:
    """Os dois limites de um grupo no mês."""

    grupo: str
    itens: int
    unidades: float
    margem_total: float
    margem_media_unitaria: float
    limiar_popularidade_pct: float


def _classe(popular: bool, margem_alta: bool) -> str:
    if popular:
        return ESTRELA if margem_alta else BURRO_DE_CARGA
    return QUEBRA_CABECA if margem_alta else CAO


def classificar(
    itens: list[ItemMes], *, venda_minima: float = VENDA_MINIMA
) -> tuple[list[Corte], list[dict]]:
    """(cortes por grupo, itens classificados).

    Entram na matriz os itens com unidade e com venda de pelo menos
    `venda_minima` no mês.
    """
    validos = [i for i in itens if i.quantidade > 0 and i.venda >= max(venda_minima, 0.01)]
    cortes: list[Corte] = []
    linhas: list[dict] = []
    for grupo in sorted({i.grupo for i in validos}):
        do_grupo = [i for i in validos if i.grupo == grupo]
        unidades = sum(i.quantidade for i in do_grupo)
        margem_total = sum(i.venda - i.custo for i in do_grupo)
        media = margem_total / unidades
        limiar = FATOR_POPULARIDADE / len(do_grupo)
        cortes.append(
            Corte(
                grupo=grupo,
                itens=len(do_grupo),
                unidades=round(unidades, 3),
                margem_total=round(margem_total, 2),
                margem_media_unitaria=round(media, 2),
                limiar_popularidade_pct=round(limiar * 100, 2),
            )
        )
        for item in do_grupo:
            margem_unit = (item.venda - item.custo) / item.quantidade
            popularidade = item.quantidade / unidades
            linhas.append(
                _linha(
                    item,
                    popularidade=popularidade,
                    classe=_classe(popularidade >= limiar, margem_unit >= media),
                )
            )
    # Dentro de cada grupo, o que mais pesa na margem primeiro.
    linhas.sort(key=lambda linha: (linha["grupo"], -linha["margem_total"], linha["nome"]))
    return cortes, linhas


def _linha(item: ItemMes, *, popularidade: float | None, classe: str | None) -> dict:
    return {
        "nome": item.nome,
        "grupo": item.grupo,
        "subgrupo": item.subgrupo,
        "quantidade": round(item.quantidade, 3),
        "venda_liquida": round(item.venda, 2),
        "custo": round(item.custo, 2),
        "preco_medio": round(item.venda / item.quantidade, 2),
        "custo_unitario": round(item.custo / item.quantidade, 2),
        "margem_unitaria": round((item.venda - item.custo) / item.quantidade, 2),
        "margem_total": round(item.venda - item.custo, 2),
        "cmv_pct": round(item.custo / item.venda * 100, 2),
        "popularidade_pct": round(popularidade * 100, 2) if popularidade is not None else None,
        "classe": classe,
        "abaixo_do_custo": item.custo > item.venda,
    }


def abaixo_do_custo(itens: list[ItemMes], classificados: list[dict]) -> list[dict]:
    """Itens vendidos abaixo do custo da ficha, do maior prejuízo ao menor.

    Olha TODOS os itens do mês, não só os da matriz: a jarra de limão da casa
    piloto vende pouco, mas perde R$ 27 por unidade. Fica fora só o preço
    simbólico (cortesia). Quem está na matriz vem com o quadrante.
    """
    classe = {linha["nome"]: linha["classe"] for linha in classificados}
    popularidade = {linha["nome"]: linha["popularidade_pct"] / 100 for linha in classificados}
    linhas = [
        _linha(i, popularidade=popularidade.get(i.nome), classe=classe.get(i.nome))
        for i in itens
        if i.quantidade > 0
        and i.venda > 0
        and i.venda / i.quantidade >= PRECO_SIMBOLICO
        and i.custo > i.venda
    ]
    return sorted(linhas, key=lambda linha: (linha["margem_total"], linha["nome"]))


def fora_da_matriz(itens: list[ItemMes], grupo: str, *, venda_minima: float = VENDA_MINIMA) -> int:
    """Itens do grupo vendidos no mês que ficaram fora da matriz por volume."""
    return sum(
        1 for i in itens if i.grupo == grupo and i.quantidade > 0 and 0 < i.venda < venda_minima
    )


def contagem(linhas: list[dict], grupo: str) -> dict[str, int]:
    """Quantos itens do grupo em cada quadrante (sempre as quatro chaves)."""
    total = dict.fromkeys(CLASSES, 0)
    for linha in linhas:
        if linha["grupo"] == grupo:
            total[linha["classe"]] += 1
    return total
