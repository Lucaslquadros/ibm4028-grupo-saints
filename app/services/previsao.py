"""Previsão de demanda por item — RF07.

**Não é machine learning, e chamar de IA seria mentira.** É média móvel com
ajuste de tendência e de sazonalidade: três linhas de estatística descritiva que
qualquer pessoa confere na mão. A escolha é deliberada — com 24 meses de
histórico mensal e no máximo duas observações por mês do ano, um modelo
treinado não teria dado para aprender nada que isto já não capture, e teria a
desvantagem de ninguém poder auditar o número.

O que o cliente disse na entrevista de 01/09/2026, e que originou o RF07:
"a gente não tem uma inteligência [...] você parte do senso do chefe".

Limite honesto, que aparece na resposta da API e na tela
---------------------------------------------------------
O sistema **não sabe o estoque atual** — ele lê relatórios de venda e de
compra, nunca uma contagem. Então o que ele calcula é **demanda esperada** para
o próximo período. A sugestão de compra assume estoque inicial zero e é, por
isso, um **teto**: quem compra precisa subtrair o que já tem na prateleira.
Entregar isso como "compre exatamente X" seria o mesmo erro de apresentar o
ajuste de CMV como se fosse economia.

Também não modela: prazo de entrega do fornecedor, lote mínimo de compra,
validade do produto e ruptura passada (item que vendeu pouco porque faltou,
não porque não havia demanda — este último enviesa a média para baixo).
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass, field

# Janela da média móvel. Três meses é curto o bastante para acompanhar mudança
# de patamar e longo o bastante para não perseguir um mês atípico.
MESES_BASE = 3
# Tendência exige duas janelas completas para comparar.
MESES_PARA_TENDENCIA = MESES_BASE * 2
# Sazonalidade exige um ano para que exista "o mesmo mês do ano passado".
MESES_PARA_SAZONALIDADE = 12

# Limites de segurança. Sem eles, um item que vendeu 2 unidades num mês e 200 no
# seguinte produz tendência de +9900% e uma sugestão absurda.
LIMITE_TENDENCIA = 0.5  # ±50%
LIMITE_SAZONAL_MIN, LIMITE_SAZONAL_MAX = 0.5, 2.0
# E um limite sobre o resultado final, relativo à própria média: nenhum ajuste
# justifica sugerir menos de um terço ou mais que o triplo da média recente.
LIMITE_FINAL_MIN, LIMITE_FINAL_MAX = 1 / 3, 3.0

CV_CONFIANCA_ALTA = 0.30  # coeficiente de variação


@dataclass
class Ponto:
    periodo: str  # AAAA-MM
    quantidade: float


@dataclass
class Previsao:
    nome: str
    grupo: str
    subgrupo: str | None
    periodo_alvo: str
    meses_com_dado: int
    media_recente: float
    tendencia_pct: float | None
    indice_sazonal: float | None
    demanda_prevista: float
    sugestao_compra: float
    confianca: str  # alta | media | baixa
    motivo_confianca: str
    historico: list[Ponto] = field(default_factory=list)


# Quanto o volume do mês-base pode fugir da mediana antes de virar aviso.
DESVIO_VOLUME_SUSPEITO = 0.20


def alerta_volume(series: list[list[Ponto]], periodo_base: str) -> str | None:
    """Avisa quando o mês-base tem volume total muito fora do padrão da série.

    Por que isto existe: na base real do cliente, set/26 vendeu 75% da média dos
    24 meses — e **todos** os itens apareceram com tendência de queda, porque a
    média móvel e a tendência leem a última observação. Queda uniforme em todo o
    catálogo quase nunca é mercado; costuma ser relatório incompleto (export
    tirado antes do fim do mês, aba do mês ainda em edição).

    O sistema não tem como saber qual dos dois é — nada no arquivo diz se o mês
    fechou. Então ele não corrige nada: avisa, e quem decide julga. Corrigir por
    conta própria seria inventar venda que talvez não exista.
    """
    if not series:
        return None

    total_por_periodo: dict[str, float] = {}
    for serie in series:
        for ponto in serie:
            total_por_periodo[ponto.periodo] = (
                total_por_periodo.get(ponto.periodo, 0.0) + ponto.quantidade
            )

    base = total_por_periodo.pop(periodo_base, None)
    if base is None or len(total_por_periodo) < MESES_BASE:
        return None

    # Mediana, não média: um único mês atípico não deve mover a referência.
    referencia = statistics.median(total_por_periodo.values())
    if referencia == 0:
        return None

    proporcao = base / referencia
    if abs(proporcao - 1) < DESVIO_VOLUME_SUSPEITO:
        return None

    if proporcao < 1:
        return (
            f"O volume vendido em {periodo_base} foi {(1 - proporcao):.0%} abaixo da mediana "
            "dos outros meses, em todos os itens ao mesmo tempo. Se o relatório do mês "
            "estiver incompleto, a previsão abaixo está subestimada — confira se o export "
            "cobre o mês fechado."
        )
    return (
        f"O volume vendido em {periodo_base} foi {(proporcao - 1):.0%} acima da mediana dos "
        "outros meses, em todos os itens ao mesmo tempo. Confirme se foi um mês atípico "
        "(evento, feriado) antes de usar a previsão abaixo."
    )


def proximo_periodo(periodo: str) -> str:
    """'2026-09' → '2026-10'. '2026-12' → '2027-01'."""
    ano, mes = (int(p) for p in periodo.split("-"))
    return f"{ano + 1}-01" if mes == 12 else f"{ano}-{mes + 1:02d}"


def _media(valores: list[float]) -> float:
    return sum(valores) / len(valores) if valores else 0.0


def _tendencia(quantidades: list[float]) -> float | None:
    """Variação entre a média das últimas 3 observações e a das 3 anteriores.

    `None` quando não há duas janelas completas — melhor devolver "não sei" do
    que devolver 0 e deixar quem lê achar que a demanda está estável.
    """
    if len(quantidades) < MESES_PARA_TENDENCIA:
        return None
    recente = _media(quantidades[-MESES_BASE:])
    anterior = _media(quantidades[-MESES_PARA_TENDENCIA:-MESES_BASE])
    if anterior == 0:
        return None
    bruta = recente / anterior - 1
    return max(-LIMITE_TENDENCIA, min(LIMITE_TENDENCIA, bruta))


def _mes(periodo: str) -> str:
    return periodo.split("-")[1]


def _indices_sazonais(historico: list[Ponto]) -> dict[str, float]:
    """{mês do ano: índice}. Quanto cada mês costuma fugir da média anual.

    Ex.: dezembro vendendo 40% acima da média dá índice 1,4. Dicionário vazio
    sem um ano de histórico — aí não existe "o mesmo mês do ano passado".
    """
    if len(historico) < MESES_PARA_SAZONALIDADE:
        return {}
    geral = _media([p.quantidade for p in historico])
    if geral == 0:
        return {}

    por_mes: dict[str, list[float]] = {}
    for ponto in historico:
        por_mes.setdefault(_mes(ponto.periodo), []).append(ponto.quantidade)
    return {
        mes: max(LIMITE_SAZONAL_MIN, min(LIMITE_SAZONAL_MAX, _media(valores) / geral))
        for mes, valores in por_mes.items()
    }


def _dessazonalizar(historico: list[Ponto], indices: dict[str, float]) -> list[float]:
    """Remove o efeito do mês antes de medir patamar e tendência.

    Sem este passo o cálculo se contamina: numa série de 100/mês com dezembro
    de 200, prever janeiro dava 164, porque o pico de dezembro entrava na média
    móvel **e** inflava a tendência, e o índice de janeiro corrigia só parte.
    Dessazonalizada, a série fica plana, a tendência volta a zero e janeiro é
    previsto em 100 — que é a resposta certa.
    """
    return [p.quantidade / indices.get(_mes(p.periodo), 1.0) for p in historico]


def _confianca(quantidades: list[float]) -> tuple[str, str]:
    """(nível, motivo). O motivo vai para a tela: número sem qualificação vira
    decisão errada, e quem decide tem o direito de saber o quanto confiar."""
    meses = len(quantidades)
    if meses < MESES_BASE:
        return "baixa", f"só {meses} {'mês' if meses == 1 else 'meses'} de histórico"

    media = _media(quantidades)
    if media == 0:
        return "baixa", "sem venda registrada no histórico"
    cv = statistics.pstdev(quantidades) / media if meses > 1 else 0.0

    if meses >= MESES_PARA_SAZONALIDADE and cv <= CV_CONFIANCA_ALTA:
        return "alta", f"{meses} meses de histórico e venda estável (variação {cv:.0%})"
    if meses >= MESES_PARA_TENDENCIA:
        if cv > CV_CONFIANCA_ALTA:
            return "media", f"{meses} meses, mas a venda oscila muito (variação {cv:.0%})"
        return "media", f"{meses} meses de histórico, menos de um ano"
    return "baixa", f"{meses} meses de histórico, pouco para ver tendência"


def prever(
    *,
    nome: str,
    grupo: str,
    subgrupo: str | None,
    historico: list[Ponto],
    periodo_alvo: str,
    margem_seguranca_pct: float = 10.0,
) -> Previsao:
    """Demanda esperada do item no `periodo_alvo`, a partir do histórico de venda.

    O histórico deve vir em ordem cronológica. Meses sem venda do item
    simplesmente não aparecem — e isso é uma limitação conhecida: não
    distinguimos "não vendeu" de "não estava no cardápio".
    """
    ordenado = sorted(historico, key=lambda p: p.periodo)
    quantidades = [p.quantidade for p in ordenado]

    indices = _indices_sazonais(ordenado)
    ajustadas = _dessazonalizar(ordenado, indices)

    # Patamar e tendência saem da série SEM efeito de mês; o efeito volta no fim,
    # aplicado ao mês-alvo. Medir tendência na série crua confunde "está
    # crescendo" com "dezembro chegou".
    base = _media(ajustadas[-MESES_BASE:])
    tendencia = _tendencia(ajustadas)
    sazonal = indices.get(_mes(periodo_alvo))

    prevista = base * (1 + (tendencia or 0.0)) * (sazonal or 1.0)

    # `media_recente` é a média CRUA dos últimos meses — é o número que o
    # usuário consegue conferir na própria planilha. A base dessazonalizada é
    # detalhe interno e exibi-la só geraria desconfiança ("essa média está errada").
    media_recente = _media(quantidades[-MESES_BASE:])
    # Trava final relativa à média crua: rede de segurança para o caso em que os
    # índices sazonais foram travados e a base dessazonalizada saiu distorcida.
    prevista = max(
        media_recente * LIMITE_FINAL_MIN, min(media_recente * LIMITE_FINAL_MAX, prevista)
    )

    confianca, motivo = _confianca(quantidades)
    return Previsao(
        nome=nome,
        grupo=grupo,
        subgrupo=subgrupo,
        periodo_alvo=periodo_alvo,
        meses_com_dado=len(ordenado),
        media_recente=round(media_recente, 2),
        tendencia_pct=round(tendencia * 100, 2) if tendencia is not None else None,
        indice_sazonal=round(sazonal, 3) if sazonal is not None else None,
        demanda_prevista=round(prevista, 2),
        sugestao_compra=round(prevista * (1 + margem_seguranca_pct / 100), 2),
        confianca=confianca,
        motivo_confianca=motivo,
        historico=ordenado,
    )
