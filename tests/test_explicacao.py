"""Explicação do ajuste — RF11 (docs/11-ciclo-explicacao-do-ajuste.md, 3.7).

Duas camadas, de propósito:

- As regras de **sinal, compensação e texto** são testadas direto em
  `app/services/explicacao.py`, com números na mão. É função pura, sem banco:
  teste de texto não precisa de upload nem de fixture de HTTP.
- O que depende do `GROUP BY` (contribuições que somam, subgrupo com e sem par,
  grupo sem par no mês) é testado pela API, com as planilhas sintéticas de
  `tests/planilhas.py`.

Nenhum número da casa real aparece aqui: o fechamento de set/26 (−3,68 pp) é
conferido à mão depois do deploy (regra 7 do ciclo).
"""

import io

import pytest

from app.services.explicacao import (
    LIMIAR_PP,
    TOLERANCIA_SOMA_PP,
    LinhaSubgrupo,
    explicar,
)
from tests.planilhas import (
    cardapio_xlsx,
    dre_xlsx,
    planilha_real_xlsx,
    planilha_teorico_xlsx,
    xlsx,
)

CASAS = "/api/v1/casas"
UPLOADS = "/api/v1/uploads-custo"
FECHAMENTO = "/api/v1/metricas/fechamento"
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
PERIODO = "2026-09"


# ----------------------------------------------------- regras puras (sem banco)
def _grupo(nome: str, *, teorico: float | None, real: float | None, venda: float) -> dict:
    """Uma linha de grupo do fechamento, no formato de `crud._montar_linha`."""
    ajuste = None if teorico is None or real is None else round(real - teorico, 2)
    return {
        "grupo": nome,
        "venda_liquida": venda,
        "custo_teorico": teorico,
        "custo_real": real,
        "ajuste": ajuste,
        "ajuste_pp": None if ajuste is None else round(ajuste / venda * 100, 2),
    }


def _total(grupos: list[dict]) -> dict:
    """O TOTAL como `crud._fechamentos` monta: lado sem nenhum grupo fica None,
    e não zero. A diferença importa — zero geraria um ajuste inventado."""

    def soma(campo: str) -> float | None:
        valores = [g[campo] for g in grupos if g[campo] is not None]
        return sum(valores) if valores else None

    return _grupo(
        "TOTAL",
        teorico=soma("custo_teorico"),
        real=soma("custo_real"),
        venda=sum(g["venda_liquida"] for g in grupos),
    )


def test_ajuste_acima_do_limiar_nomeia_o_grupo_principal():
    """+3,33 pp: real acima do teórico, a situação "clássica" de perda."""
    grupos = [
        _grupo("MEDICAMENTOS", teorico=650, real=700, venda=1500),
        _grupo("PERFUMARIA", teorico=300, real=320, venda=600),
    ]

    exp = explicar(periodo=PERIODO, total=_total(grupos), grupos=grupos)

    assert exp["situacao"] == "acima"
    assert exp["limiar_pp"] == LIMIAR_PP
    assert "acima do previsto" in exp["resumo"]
    assert "MEDICAMENTOS" in exp["resumo"]  # maior |contribuição| (+2,38 pp)
    assert 1 <= len(exp["sugestoes"]) <= 2
    assert any("perdas" in s for s in exp["sugestoes"])


def test_ajuste_abaixo_do_limiar_nao_e_tratado_como_economia():
    """O caso da casa piloto em set/26. Uma frase de "gastou a mais" seria
    falsa, e "economizou" seria pior: real abaixo do teórico costuma ser
    compra não lançada ou inventário superestimado."""
    grupos = [
        _grupo("ALIMENTOS", teorico=400, real=300, venda=1000),
        _grupo("BEBIDAS", teorico=500, real=450, venda=2000),
    ]

    exp = explicar(periodo=PERIODO, total=_total(grupos), grupos=grupos)

    assert exp["situacao"] == "abaixo"
    assert "abaixo do previsto" in exp["resumo"]
    assert "economia" not in exp["resumo"]
    assert "a mais" not in exp["resumo"]
    assert any("lançadas" in s and "inventário" in s for s in exp["sugestoes"]), exp["sugestoes"]
    assert len(exp["sugestoes"]) <= 2


def test_ajuste_dentro_da_margem_nao_sugere_acao():
    grupos = [
        _grupo("ALIMENTOS", teorico=300, real=305, venda=1000),
        _grupo("BEBIDAS", teorico=400, real=402, venda=2000),
    ]

    exp = explicar(periodo=PERIODO, total=_total(grupos), grupos=grupos)

    assert exp["situacao"] == "dentro"
    assert exp["sugestoes"] == []
    assert "margem esperada" in exp["resumo"]


def test_grupos_de_sinais_opostos_declaram_a_compensacao():
    """Total pequeno escondendo dois desvios grandes: ALIMENTOS +2,0 pp e
    BEBIDAS −1,5 pp do total resultam em +0,5 pp. Sem a frase da compensação,
    "dentro da margem" seria conclusão falsa."""
    grupos = [
        _grupo("ALIMENTOS", teorico=300, real=360, venda=1000),
        _grupo("BEBIDAS", teorico=400, real=355, venda=2000),
    ]

    exp = explicar(periodo=PERIODO, total=_total(grupos), grupos=grupos)

    assert exp["situacao"] == "dentro"
    assert "compensou" in exp["resumo"]
    assert "ALIMENTOS ficou acima" in exp["resumo"]
    assert "BEBIDAS abaixo" in exp["resumo"]


def test_subgrupo_comparado_entra_na_sugestao_quando_existe_nos_dois_lados():
    grupos = [_grupo("ALIMENTOS", teorico=300, real=360, venda=1000)]
    subgrupos = [
        LinhaSubgrupo(
            tipo="cardapio", grupo="ALIMENTOS", subgrupo="PETISCOS", custo=300, venda=1000
        ),
        LinhaSubgrupo(tipo="compras", grupo="ALIMENTOS", subgrupo="PETISCOS", custo=360),
    ]

    exp = explicar(periodo=PERIODO, total=_total(grupos), grupos=grupos, subgrupos=subgrupos)

    assert "PETISCOS" in exp["sugestoes"][0]
    assert exp["subgrupos_comparados"][0]["ajuste"] == 60.0
    assert exp["subgrupos_comparados"][0]["ajuste_pp"] == 6.0


def test_sem_ajuste_no_total_nao_ha_explicacao():
    """Mês com um lado só: a tela já diz qual relatório falta. Gerar texto
    sobre um ajuste que não existe seria inventar diagnóstico (docs/11, 3.4)."""
    grupos = [_grupo("ALIMENTOS", teorico=300, real=None, venda=1000)]

    assert explicar(periodo=PERIODO, total=_total(grupos), grupos=grupos) is None


# ------------------------------------------------------------- pela API (banco)
@pytest.fixture
def casa_id(client) -> int:
    casa = {"nome": "Boteco São Bento - Vila Madalena", "marca": "Boteco São Bento",
            "cidade": "São Paulo"}  # fmt: skip
    return client.post(CASAS, json=casa).json()["id"]


@pytest.fixture
def farmacia_id(client) -> int:
    unidade = {"nome": "Drogaria Central - Centro", "marca": "Drogaria Central",
               "cidade": "São Paulo"}  # fmt: skip
    return client.post(CASAS, json=unidade).json()["id"]


def _enviar(client, casa_id, tipo, conteudo, periodo=PERIODO):
    resposta = client.post(
        UPLOADS,
        data={"casa_id": casa_id, "periodo": periodo, "tipo": tipo},
        files={"arquivo": ("export.xlsx", io.BytesIO(conteudo), XLSX)},
    )
    assert resposta.status_code == 201, resposta.text


def test_soma_das_contribuicoes_bate_com_o_ajuste_do_total(client, farmacia_id):
    """Teste obrigatório do ciclo (docs/11, 3.1). O `ajuste_pp` de cada grupo
    usa a venda do próprio grupo e **não** soma ao total; a contribuição soma.
    Se esta invariante cair, a frase "principalmente em Y" perde o apoio."""
    _enviar(client, farmacia_id, "cardapio", planilha_teorico_xlsx())
    _enviar(client, farmacia_id, "compras", planilha_real_xlsx())

    corpo = client.get(FECHAMENTO, params={"casa_id": farmacia_id, "periodo": PERIODO}).json()
    exp = corpo["explicacao"]

    soma = sum(c["contribuicao_pp"] for c in exp["contribuicoes"])
    assert abs(soma - corpo["total"]["ajuste_pp"]) <= TOLERANCIA_SOMA_PP
    assert exp["grupos_sem_par"] == []
    assert exp["situacao"] == "acima"


def test_subgrupo_so_e_comparado_quando_existe_nos_dois_lados(client, casa_id):
    """O limite de dado do Everest, com o par sintético: no cardápio os
    subgrupos são categorias de venda (PETISCOS, CHOPP) e na DRE são categorias
    de insumo (BOVINOS, HORTIFRUTI, CHOPP). Só CHOPP existe nos dois."""
    _enviar(client, casa_id, "cardapio", cardapio_xlsx())
    _enviar(client, casa_id, "compras", dre_xlsx())

    exp = client.get(FECHAMENTO, params={"casa_id": casa_id, "periodo": PERIODO}).json()[
        "explicacao"
    ]

    assert [(s["grupo"], s["subgrupo"]) for s in exp["subgrupos_comparados"]] == [
        ("BEBIDAS", "CHOPP")
    ]
    comparado = exp["subgrupos_comparados"][0]
    assert (comparado["custo_teorico"], comparado["custo_real"]) == (400.0, 420.0)
    assert comparado["ajuste_pp"] == 1.0  # 20 ÷ 2000 de venda do subgrupo

    sem_par = {(s["subgrupo"], s["lado"]) for s in exp["subgrupos_sem_par"]}
    assert sem_par == {("PETISCOS", "teorico"), ("BOVINOS", "real"), ("HORTIFRUTI", "real")}
    # DESCARTAVEIS fica fora: MATERIAL DE CONSUMO não é CMV direto
    assert "DESCARTAVEIS" not in {s["subgrupo"] for s in exp["subgrupos_sem_par"]}
    assert "categoria de insumo" in exp["limite_dado"]


def test_grupo_com_so_um_lado_no_mes_e_declarado(client, farmacia_id):
    """PERFUMARIA tem os dois lados em agosto (então é CMV direto desta casa) e
    só o teórico em setembro. O total de setembro fica distorcido por ela — e a
    explicação **diz isso** em vez de esconder."""
    so_medicamentos = xlsx({"Dados": [["Grupo", "Custo"], ["MEDICAMENTOS", 700]]})
    _enviar(client, farmacia_id, "cardapio", planilha_teorico_xlsx(), periodo="2026-08")
    _enviar(client, farmacia_id, "compras", planilha_real_xlsx(), periodo="2026-08")
    _enviar(client, farmacia_id, "cardapio", planilha_teorico_xlsx())
    _enviar(client, farmacia_id, "compras", so_medicamentos)

    exp = client.get(FECHAMENTO, params={"casa_id": farmacia_id, "periodo": PERIODO}).json()[
        "explicacao"
    ]

    assert exp["grupos_sem_par"] == ["PERFUMARIA"]
    assert "PERFUMARIA" in exp["resumo"]
    assert "não é comparável por completo" in exp["resumo"]


def test_mes_com_um_lado_so_devolve_explicacao_nula_e_200(client, casa_id):
    _enviar(client, casa_id, "cardapio", cardapio_xlsx())

    resposta = client.get(FECHAMENTO, params={"casa_id": casa_id, "periodo": PERIODO})

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["explicacao"] is None
    assert corpo["total"]["cmv_teorico_pct"] == 23.33  # o resto do fechamento continua


def test_casa_inexistente_continua_404(client):
    assert client.get(FECHAMENTO, params={"casa_id": 999, "periodo": PERIODO}).status_code == 404
