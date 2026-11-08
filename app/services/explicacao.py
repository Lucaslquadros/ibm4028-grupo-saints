"""Explicação do ajuste de CMV — RF11 (docs/11-ciclo-explicacao-do-ajuste.md, 3).

Mostrar o ajuste não basta: o ERP do cliente já tem o número. O que o sócio
(Persona 2) não sabe é **onde procurar**. Este módulo decompõe o ajuste do mês
por grupo, decide a situação e escreve o texto — por regras, sem LLM.

Tudo aqui é **função pura**: recebe os números já somados pelo banco e devolve
dicts. Nenhuma query, nenhum import de `app.crud`. É o que permite testar o
texto com números na mão, sem fixture de banco.

Três cuidados que o ciclo tornou obrigatórios:

1. **Três ramos de sinal, nunca dois.** O ajuste da casa piloto em set/26 é
   **negativo** (real abaixo do teórico). "Gastaram X a mais" é falso para ele,
   e ajuste negativo **não é economia** — é divergência: em geral falta algo no
   lado real (compra não lançada, inventário superestimado) ou sobra no teórico
   (ficha técnica superestimada, período desalinhado).
2. **Contribuição ≠ ajuste em pp.** O `ajuste_pp` de cada grupo usa a venda do
   próprio grupo como denominador e por isso **não soma** ao total. Para dizer
   "principalmente em Y" a medida é a contribuição em pontos do total.
3. **Não inventar granularidade.** Abaixo do grupo só se compara subgrupo que
   existe nos **dois** lados; o resto é composição de custo, nunca desvio.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

LIMIAR_PP = 1.0
"""Abaixo disto, em módulo, a diferença é tratada como margem esperada.

**É premissa nossa, não veio do cliente** — e por isso volta na resposta, para
a tela poder exibir o número junto da leitura. O gabarito de fechamento da
equipe de custos nunca chegou (ver `docs/07-fechamento-cmv.md`, pendências).
"""

LIMITE_DADO = (
    "O ERP informa compras por categoria de insumo e vendas por categoria de "
    "cardápio. Abaixo do grupo, só comparamos as categorias que existem com o "
    "mesmo nome nos dois relatórios."
)
"""Texto fixo da resposta. A tela mostra sempre que houver subgrupo sem par:
comparação quase vazia na casa real é **limite do dado**, não falha do cálculo.
"""

TOLERANCIA_SOMA_PP = 0.02
"""Quanto a soma das contribuições pode fugir do ajuste total por arredondamento."""


@dataclass(frozen=True)
class LinhaSubgrupo:
    """Um (grupo, subgrupo) de um dos lados, já somado no banco."""

    tipo: str  # "cardapio" (teórico) | "compras" (real)
    grupo: str
    subgrupo: str
    custo: float
    venda: float | None = None


# ------------------------------------------------------------------ formatação
def _numero_br(valor: float, casas: int = 2) -> str:
    """1234.5 → '1.234,50'. Sempre em módulo: a direção vai nas palavras."""
    return f"{abs(valor):,.{casas}f}".translate(str.maketrans({",": ".", ".": ","}))


def _pp_com_sinal(valor: float) -> str:
    """-2.4 → '-2,40'. O sinal é explícito porque muda o diagnóstico."""
    return f"{'-' if valor < 0 else '+'}{_numero_br(valor)}"


# ------------------------------------------------------------- decomposição
def _contribuicoes(grupos: list[dict], venda_total: float) -> list[dict]:
    """`ajuste(g) ÷ venda_liquida(TOTAL) × 100`, em ordem de peso.

    Só grupos com os dois lados: sem um deles não existe ajuste a atribuir.
    Esta é a medida que **soma** ao `total.ajuste_pp` — ver teste da soma.
    """
    contribuicoes = [
        {
            "grupo": g["grupo"],
            "ajuste": g["ajuste"],
            "contribuicao_pp": round(g["ajuste"] / venda_total * 100, 2),
        }
        for g in grupos
        if g.get("ajuste") is not None
    ]
    return sorted(contribuicoes, key=lambda c: abs(c["contribuicao_pp"]), reverse=True)


def _situacao(ajuste_pp: float) -> str:
    if ajuste_pp > LIMIAR_PP:
        return "acima"
    if ajuste_pp < -LIMIAR_PP:
        return "abaixo"
    return "dentro"


def _principal(contribuicoes: list[dict], ajuste_pp: float) -> dict | None:
    """O grupo de maior |contribuição| **com o mesmo sinal do total**.

    O filtro de sinal não é detalhe: com um grupo acima e outro abaixo, o de
    maior módulo pode apontar na direção oposta à do total e a frase sairia
    contradizendo o número. Devolve None quando nenhum grupo acompanha o sinal
    — acontece quando o total está distorcido por grupo sem par, e nesse caso o
    texto simplesmente não afirma "a maior parte veio de".
    """
    mesmo_sinal = [
        c for c in contribuicoes if (c["contribuicao_pp"] > 0) == (ajuste_pp > 0) and c["ajuste"]
    ]
    return mesmo_sinal[0] if mesmo_sinal else None


def _compensacao(contribuicoes: list[dict]) -> tuple[dict, dict] | None:
    """(grupo acima, grupo abaixo) quando os dois passam do limiar.

    Um total pequeno pode esconder dois desvios grandes que se anularam. Sem
    esta frase, "dentro da margem" seria uma conclusão falsa.
    """
    acima = [c for c in contribuicoes if c["contribuicao_pp"] >= LIMIAR_PP]
    abaixo = [c for c in contribuicoes if c["contribuicao_pp"] <= -LIMIAR_PP]
    if not acima or not abaixo:
        return None
    return acima[0], abaixo[0]


def _subgrupos(
    linhas: list[LinhaSubgrupo], grupos_comparados: set[str]
) -> tuple[list[dict], list[dict]]:
    """(comparados, sem par). Só pares presentes nos **dois** lados entram.

    `grupos_comparados` restringe a grupos do CMV direto: subgrupo de custo
    indireto não tem teórico, e comparar seria inventar desvio.
    """
    teorico = {
        (linha.grupo, linha.subgrupo): linha
        for linha in linhas
        if linha.tipo == "cardapio" and linha.grupo in grupos_comparados
    }
    real = {
        (linha.grupo, linha.subgrupo): linha
        for linha in linhas
        if linha.tipo == "compras" and linha.grupo in grupos_comparados
    }

    comparados = []
    for chave in teorico.keys() & real.keys():
        lado_teorico, lado_real = teorico[chave], real[chave]
        ajuste = round(lado_real.custo - lado_teorico.custo, 2)
        venda = lado_teorico.venda
        comparados.append(
            {
                "grupo": chave[0],
                "subgrupo": chave[1],
                "custo_teorico": round(lado_teorico.custo, 2),
                "custo_real": round(lado_real.custo, 2),
                "ajuste": ajuste,
                "ajuste_pp": round(ajuste / venda * 100, 2) if venda else None,
            }
        )
    comparados.sort(key=lambda s: abs(s["ajuste"]), reverse=True)

    sem_par = [
        {
            "grupo": linha.grupo,
            "subgrupo": linha.subgrupo,
            "lado": "teorico" if linha.tipo == "cardapio" else "real",
            "custo": round(linha.custo, 2),
        }
        for origem, lado in ((teorico, real), (real, teorico))
        for chave, linha in origem.items()
        if chave not in lado
    ]
    sem_par.sort(key=lambda s: s["custo"], reverse=True)
    return comparados, sem_par


# -------------------------------------------------------------------- texto
def _frase_do_ajuste(situacao: str, periodo: str, ajuste_pp: float, ajuste: float) -> str:
    """A primeira frase. "CMV" é expandido na primeira menção: o leitor é o
    sócio, e jargão sem explicação é o que faz o painel não ser lido."""
    cmv = "o CMV (custo das mercadorias vendidas) real"
    if situacao == "acima":
        return (
            f"Em {periodo}, {cmv} ficou {_numero_br(ajuste_pp)} pontos acima do previsto "
            f"pelas fichas técnicas (R$ {_numero_br(ajuste)} a mais)."
        )
    if situacao == "abaixo":
        # Nenhuma palavra de ganho aqui, e nada de "a mais": o número é negativo
        # e a leitura é divergência, não eficiência.
        return (
            f"Em {periodo}, {cmv} ficou {_numero_br(ajuste_pp)} pontos abaixo do previsto "
            f"pelas fichas técnicas (R$ {_numero_br(ajuste)} a menos). Diferença nesse "
            "sentido costuma apontar algo faltando no lado real — compra não lançada, "
            "inventário de fim de mês superestimado — ou sobrando no teórico."
        )
    return (
        f"Em {periodo}, a diferença entre {cmv} e o previsto pelas fichas técnicas ficou "
        f"dentro da margem esperada de {_numero_br(LIMIAR_PP, 1)} ponto "
        f"({_pp_com_sinal(ajuste_pp)} pp, R$ {_numero_br(ajuste)})."
    )


def _resumo(
    *,
    situacao: str,
    periodo: str,
    ajuste_pp: float,
    ajuste: float,
    principal: dict | None,
    compensacao: tuple[dict, dict] | None,
    grupos_sem_par: list[str],
) -> str:
    frases = [_frase_do_ajuste(situacao, periodo, ajuste_pp, ajuste)]

    if situacao != "dentro" and principal is not None:
        # Com grupo sem par, o total não é a soma das contribuições, e "a maior
        # parte veio de X" descreveria mal o número. A frase então se limita ao
        # que é de fato comparável.
        abertura = (
            "Entre os grupos com os dois lados, o maior desvio veio de"
            if grupos_sem_par
            else "A maior parte veio de"
        )
        frases.append(
            f"{abertura} {principal['grupo']} ({_pp_com_sinal(principal['contribuicao_pp'])} pp)."
        )

    if compensacao is not None:
        acima, abaixo = compensacao
        frases.append(
            f"{acima['grupo']} ficou acima e {abaixo['grupo']} abaixo; no total, um "
            "compensou parte do outro."
        )

    if grupos_sem_par:
        frases.append(
            f"O total não é comparável por completo: {_lista(grupos_sem_par)} "
            f"{'têm' if len(grupos_sem_par) > 1 else 'tem'} só um dos dois lados neste mês."
        )

    return " ".join(frases)


def _lista(nomes: list[str]) -> str:
    """['A'] → 'A'; ['A','B'] → 'A e B'; ['A','B','C'] → 'A, B e C'."""
    if len(nomes) == 1:
        return nomes[0]
    return f"{', '.join(nomes[:-1])} e {nomes[-1]}"


def _sugestoes(
    *,
    situacao: str,
    principal: dict | None,
    subgrupo_suspeito: dict | None,
    grupos_sem_par: list[str],
) -> list[str]:
    """No máximo duas, sempre acionáveis e na direção certa do sinal.

    Fora: "contar esses itens semanalmente". A Persona 1 já faz contagem
    semanal dos itens principais (`docs/01-requisitos.md`, Persona 1) — para
    ela seria ruído, e sugestão que o usuário já cumpre queima a confiança no
    resto da tela.
    """
    if situacao == "dentro":
        # Compensação aparece no resumo, não aqui: "dentro da margem" não gera ação.
        return []

    if principal is None:
        if grupos_sem_par:
            return [
                f"Enviar o relatório que falta para {_lista(grupos_sem_par)}: o ajuste do "
                "mês está sendo puxado por grupo que só tem um dos dois lados."
            ]
        return []

    grupo = principal["grupo"]
    if situacao == "acima":
        onde = f" em {grupo}"
        if subgrupo_suspeito is not None:
            onde += f", começando por {subgrupo_suspeito['subgrupo']}"
        return [
            f"Investigar perdas, quebras e desvios{onde}.",
            f"Conferir se as fichas técnicas de {grupo} estão com o custo atualizado — "
            "ficha subestimada produz o mesmo efeito.",
        ]
    return [
        f"Conferir se todas as compras de {grupo} do mês foram lançadas e se o inventário "
        "de fim de mês não está superestimado.",
        f"Confirmar que os dois relatórios são do mesmo período e conferir as fichas "
        f"técnicas de {grupo} — ficha superestimada produz o mesmo efeito.",
    ]


def _subgrupo_suspeito(comparados: list[dict], grupo: str, ajuste_pp: float) -> dict | None:
    """O subgrupo comparado de maior |ajuste| no grupo principal, no mesmo
    sentido do total. None quando o dado não desce até aí — e aí a sugestão
    fica no nível do grupo, em vez de inventar granularidade."""
    candidatos = [
        s
        for s in comparados
        if s["grupo"] == grupo and s["ajuste"] and (s["ajuste"] > 0) == (ajuste_pp > 0)
    ]
    return candidatos[0] if candidatos else None


# --------------------------------------------------------------------- entrada
def explicar(
    *,
    periodo: str,
    total: dict,
    grupos: list[dict],
    subgrupos: list[LinhaSubgrupo] | None = None,
) -> dict[str, Any] | None:
    """A explicação do mês, ou None quando não há ajuste para explicar.

    `total` e `grupos` são as linhas do fechamento (`crud._montar_linha`).
    None quando falta um dos lados: a tela já avisa qual relatório falta, e
    gerar texto sobre um ajuste inexistente seria inventar diagnóstico.
    """
    ajuste_pp = total.get("ajuste_pp")
    ajuste = total.get("ajuste")
    venda_total = total.get("venda_liquida")
    if ajuste_pp is None or ajuste is None or not venda_total:
        return None

    contribuicoes = _contribuicoes(grupos, venda_total)
    grupos_sem_par = sorted(g["grupo"] for g in grupos if g.get("ajuste") is None)
    situacao = _situacao(ajuste_pp)
    principal = _principal(contribuicoes, ajuste_pp)
    comparados, sem_par = _subgrupos(
        subgrupos or [], {c["grupo"] for c in contribuicoes} | set(grupos_sem_par)
    )

    return {
        "situacao": situacao,
        "limiar_pp": LIMIAR_PP,
        "resumo": _resumo(
            situacao=situacao,
            periodo=periodo,
            ajuste_pp=ajuste_pp,
            ajuste=ajuste,
            principal=principal,
            compensacao=_compensacao(contribuicoes),
            grupos_sem_par=grupos_sem_par,
        ),
        "sugestoes": _sugestoes(
            situacao=situacao,
            principal=principal,
            subgrupo_suspeito=(
                _subgrupo_suspeito(comparados, principal["grupo"], ajuste_pp)
                if principal is not None
                else None
            ),
            grupos_sem_par=grupos_sem_par,
        ),
        "contribuicoes": contribuicoes,
        "grupos_sem_par": grupos_sem_par,
        "subgrupos_comparados": comparados,
        "subgrupos_sem_par": sem_par,
        "limite_dado": LIMITE_DADO,
    }
