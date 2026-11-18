"""Engenharia de cardápio — a matriz popularidade × margem (RF16).

O método é o de Kasavana & Smith (1982), o padrão da gestão de restaurantes, e
dá nome ao relatório que o cliente já exporta do Everest. Cada item vendido no
mês cai num de quatro quadrantes, e cada quadrante tem uma ação conhecida:

    popular + margem alta   ESTRELA          manter e proteger
    popular + margem baixa  BURRO DE CARGA   reajustar preço ou porção
    pouco   + margem alta   QUEBRA-CABEÇA    promover, reposicionar no cardápio
    pouco   + margem baixa  CÃO              reformular ou tirar

Os dois cortes, dentro de cada CATEGORIA de cardápio — o método compara itens
que competem entre si: chopp com chopp, petisco com petisco. A categoria é o
subgrupo do relatório do ERP (CHOPP, CERVEJAS, PETISCOS, GRELHADOS…); subgrupo
com menos de `MIN_ITENS_CATEGORIA` itens no mês entra em "OUTROS" do grupo,
para não sair quadrante de um item só. Até 18/11 o corte era por grupo, e o
Chopp Claro era comparado com uma garrafa de Ketel One:

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

MIN_ITENS_CATEGORIA = 4
"""Subgrupo com menos itens que isso no mês vira "OUTROS" do grupo."""

OUTROS = "OUTROS"

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
    """Os dois limites de uma categoria de cardápio no mês."""

    grupo: str
    categoria: str
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
    """(cortes por categoria, itens classificados).

    Entram na matriz os itens com unidade e com venda de pelo menos
    `venda_minima` no mês.
    """
    validos = [i for i in itens if i.quantidade > 0 and i.venda >= max(venda_minima, 0.01)]
    categoria = categorias(validos)
    cortes: list[Corte] = []
    linhas: list[dict] = []
    chaves = {(i.grupo, categoria[i.nome]) for i in validos}
    for grupo, cat in sorted(chaves, key=lambda k: (k[0], k[1] == OUTROS, k[1])):
        da_categoria = [i for i in validos if i.grupo == grupo and categoria[i.nome] == cat]
        unidades = sum(i.quantidade for i in da_categoria)
        margem_total = sum(i.venda - i.custo for i in da_categoria)
        media = margem_total / unidades
        limiar = FATOR_POPULARIDADE / len(da_categoria)
        cortes.append(
            Corte(
                grupo=grupo,
                categoria=cat,
                itens=len(da_categoria),
                unidades=round(unidades, 3),
                margem_total=round(margem_total, 2),
                margem_media_unitaria=round(media, 2),
                limiar_popularidade_pct=round(limiar * 100, 2),
            )
        )
        for item in da_categoria:
            margem_unit = (item.venda - item.custo) / item.quantidade
            popularidade = item.quantidade / unidades
            linhas.append(
                _linha(
                    item,
                    popularidade=popularidade,
                    classe=_classe(popularidade >= limiar, margem_unit >= media),
                    categoria=cat,
                )
            )
    # Dentro de cada categoria, o que mais pesa na margem primeiro.
    ordem = {(c.grupo, c.categoria): n for n, c in enumerate(cortes)}
    linhas.sort(
        key=lambda linha: (
            ordem[(linha["grupo"], linha["categoria"])],
            -linha["margem_total"],
            linha["nome"],
        )
    )
    return cortes, linhas


def categorias(itens: list[ItemMes]) -> dict[str, str]:
    """{nome do item: categoria}. Subgrupo com menos de MIN_ITENS_CATEGORIA itens
    (ou sem subgrupo) vira OUTROS do grupo."""
    contagem_sub: dict[tuple[str, str | None], int] = {}
    for i in itens:
        chave = (i.grupo, i.subgrupo)
        contagem_sub[chave] = contagem_sub.get(chave, 0) + 1
    return {
        i.nome: i.subgrupo
        if i.subgrupo and contagem_sub[(i.grupo, i.subgrupo)] >= MIN_ITENS_CATEGORIA
        else OUTROS
        for i in itens
    }


def _linha(
    item: ItemMes, *, popularidade: float | None, classe: str | None, categoria: str | None
) -> dict:
    return {
        "nome": item.nome,
        "grupo": item.grupo,
        "subgrupo": item.subgrupo,
        "categoria": categoria,
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
    por_nome = {linha["nome"]: linha for linha in classificados}
    linhas = [
        _linha(
            i,
            popularidade=por_nome[i.nome]["popularidade_pct"] / 100 if i.nome in por_nome else None,
            classe=por_nome[i.nome]["classe"] if i.nome in por_nome else None,
            categoria=por_nome[i.nome]["categoria"] if i.nome in por_nome else None,
        )
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


def contagem(linhas: list[dict], grupo: str, categoria: str) -> dict[str, int]:
    """Quantos itens da categoria em cada quadrante (sempre as quatro chaves)."""
    total = dict.fromkeys(CLASSES, 0)
    for linha in linhas:
        if linha["grupo"] == grupo and linha["categoria"] == categoria:
            total[linha["classe"]] += 1
    return total
