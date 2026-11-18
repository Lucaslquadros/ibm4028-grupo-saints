"""Margem por item — onde o cardápio perdeu margem, em reais.

Por que existe: o fechamento por grupo diz *que* BEBIDAS ficou acima do
previsto, mas a decisão do sócio é por item — reajustar o preço, renegociar
o insumo, revisar a ficha técnica, tirar do cardápio. E a categoria esconde o
item: na casa piloto, de set/25 para set/26, BEBIDAS melhorou como um todo
(o chopp subiu de preço) enquanto a cerveja de garrafa perdeu 7 pontos.

O que se compara: o mesmo item em dois meses do **cardápio** (lado teórico:
custo da ficha técnica e venda). Não depende do lado real nem do estoque, então
funciona com o dado que toda casa já manda.

    custo extra = custo do item no mês − venda do mês × CMV do item no mês-base

é quanto o item custou a mais do que custaria se tivesse mantido a margem do
mês-base. Ordena-se por ele, não pelo CMV%: um item de CMV alto e venda
pequena pesa menos que um de CMV médio e venda grande.

Funções puras: a consulta (GROUP BY por item) fica em `crud`.
"""

from dataclasses import dataclass

LIMIAR_PP = 1.0
"""Variação de CMV do item, em pontos, a partir da qual ele conta como "perdeu
margem". Mesma premissa do fechamento (±1 ponto) — nossa, não do cliente."""

VENDA_MINIMA = 500.0
"""Item com venda abaixo disso, em qualquer dos dois meses, fica fora: com
poucas unidades o CMV% oscila por arredondamento e não por custo."""


@dataclass(frozen=True)
class ItemMes:
    """Um item do cardápio somado no mês (o mesmo nome pode vir em mais de uma
    linha do relatório)."""

    nome: str
    grupo: str
    subgrupo: str | None
    quantidade: float
    venda: float
    custo: float


def escolher_base(periodos: list[str], periodo: str) -> tuple[str, str] | None:
    """(mês-base, critério em português) entre os meses com cardápio.

    1. o mesmo mês do ano anterior, se houver — setembro contra setembro tira
       a sazonalidade da conta;
    2. senão, o mês mais antigo dos últimos 12 (o maior intervalo disponível);
    3. senão, o mês com dado mais recente antes do período.
    `None` se não há nenhum mês anterior para comparar.
    """
    anteriores = sorted(p for p in periodos if p < periodo)
    if not anteriores:
        return None
    ano, mes = (int(x) for x in periodo.split("-"))
    um_ano = f"{ano - 1:04d}-{mes:02d}"
    if um_ano in anteriores:
        return um_ano, "mesmo mês do ano anterior"
    janela = [p for p in anteriores if p > um_ano]
    if janela:
        return janela[0], "mês mais antigo com dado nos últimos 12 meses"
    return anteriores[-1], "último mês com dado antes do período"


def _variacao_pct(antes: float, depois: float) -> float | None:
    if antes == 0:
        return None
    return round((depois / antes - 1) * 100, 1) + 0.0  # + 0.0: sem "-0.0"


def comparar(
    base: dict[str, ItemMes],
    atual: dict[str, ItemMes],
    *,
    venda_minima: float = VENDA_MINIMA,
) -> list[dict]:
    """Itens presentes nos dois meses, com venda e quantidade suficientes,
    ordenados pelo custo extra (maior primeiro)."""
    linhas = []
    for nome, agora in atual.items():
        antes = base.get(nome)
        if antes is None:
            continue
        if min(antes.venda, agora.venda) < venda_minima:
            continue
        if antes.quantidade <= 0 or agora.quantidade <= 0:
            continue

        cmv_base = antes.custo / antes.venda
        cmv_atual = agora.custo / agora.venda
        custo_unit_base = antes.custo / antes.quantidade
        custo_unit_atual = agora.custo / agora.quantidade
        preco_base = antes.venda / antes.quantidade
        preco_atual = agora.venda / agora.quantidade

        linhas.append(
            {
                "nome": nome,
                "grupo": agora.grupo,
                "subgrupo": agora.subgrupo,
                "quantidade": round(agora.quantidade, 3),
                "venda_liquida": round(agora.venda, 2),
                "custo": round(agora.custo, 2),
                "cmv_base_pct": round(cmv_base * 100, 2),
                "cmv_atual_pct": round(cmv_atual * 100, 2),
                "variacao_pp": round((cmv_atual - cmv_base) * 100, 2),
                "custo_unitario_base": round(custo_unit_base, 2),
                "custo_unitario_atual": round(custo_unit_atual, 2),
                "variacao_custo_pct": _variacao_pct(custo_unit_base, custo_unit_atual),
                "preco_unitario_base": round(preco_base, 2),
                "preco_unitario_atual": round(preco_atual, 2),
                "variacao_preco_pct": _variacao_pct(preco_base, preco_atual),
                "custo_extra": round(agora.custo - agora.venda * cmv_base, 2),
            }
        )
    linhas.sort(key=lambda linha: (-linha["custo_extra"], linha["nome"]))
    return linhas


def resumo(linhas: list[dict], *, limiar_pp: float = LIMIAR_PP) -> dict:
    """Quantos itens perderam margem e quanto isso custou no mês."""
    piores = [linha for linha in linhas if linha["variacao_pp"] >= limiar_pp]
    return {
        "itens_comparados": len(linhas),
        "itens_que_pioraram": len(piores),
        "custo_extra_total": round(sum(linha["custo_extra"] for linha in piores), 2),
    }
