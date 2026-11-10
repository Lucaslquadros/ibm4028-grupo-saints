"""Compras não é consumo (10/11/2026).

A DRE gerencial do Everest traz as **compras** do mês. A planilha de
fechamento da equipe soma a variação de estoque (estoque inicial − estoque
final) à parte, e só aí existe CMV real. Estes testes cobrem:

  - o leitor da DRE no layout sem código (abas ENTRADA da planilha da equipe)
  - a base do lado real: compras (DRE), consumo (EI + C − EF), declarada
  - o texto do RF11 quando o lado real é só compras
  - o acumulado, que é a leitura que faz sentido sem inventário
"""

import io

import pytest

from app.services import explicacao
from app.services.leitores import (
    BASE_COMPRAS,
    BASE_CONSUMO,
    BASE_DECLARADA,
    TOTAL_COMPRAS,
    TOTAL_CONSUMO,
    ErroLeitura,
    base_do_total,
    ler,
    ler_compras,
    ler_planilha,
)
from tests.planilhas import (
    cardapio_xlsx,
    dre_sem_codigo_xlsx,
    dre_xlsx,
    planilha_movimento_xlsx,
    planilha_real_xlsx,
    xlsx,
)

CASAS = "/api/v1/casas"
UPLOADS = "/api/v1/uploads-custo"
FECHAMENTO = "/api/v1/metricas/fechamento"
EVOLUCAO = "/api/v1/metricas/evolucao"
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
PERIODO = "2026-09"


@pytest.fixture
def casa_id(client) -> int:
    casa = {"nome": "Casa Teste", "marca": "Teste", "cidade": "São Paulo"}
    return client.post(CASAS, json=casa).json()["id"]


def _enviar(client, casa_id, tipo, conteudo, periodo=PERIODO):
    resposta = client.post(
        UPLOADS,
        data={"casa_id": casa_id, "periodo": periodo, "tipo": tipo},
        files={"arquivo": ("export.xlsx", io.BytesIO(conteudo), XLSX)},
    )
    assert resposta.status_code == 201, resposta.text


def _fechamento(client, casa_id, periodo=PERIODO) -> dict:
    resposta = client.get(FECHAMENTO, params={"casa_id": casa_id, "periodo": periodo})
    assert resposta.status_code == 200, resposta.text
    return resposta.json()


# ------------------------------------------------------------------- leitores
def test_dre_sem_codigo_le_grupos_e_subgrupos_pela_indentacao():
    extracao = ler_compras(dre_sem_codigo_xlsx(), PERIODO)

    total = extracao.por_nivel("total")[0]
    assert total.nome == TOTAL_COMPRAS
    assert total.venda_liquida == 3200
    assert total.custo == 1000

    grupos = {g.nome: g.custo for g in extracao.por_nivel("grupo")}
    # contas zeradas (OUTROS ITENS) e o bloco depois do LUCRO BRUTO ficam fora
    assert grupos == {"ALIMENTOS": 330, "BEBIDAS": 420, "MATERIAL DE CONSUMO": 250}
    subgrupos = {s.nome: s.grupo for s in extracao.por_nivel("subgrupo")}
    assert subgrupos == {
        "BOVINOS": "ALIMENTOS",
        "HORTIFRUTI": "ALIMENTOS",
        "CHOPP": "BEBIDAS",
        "DESCARTAVEIS": "MATERIAL DE CONSUMO",
    }


def test_dre_sem_codigo_e_sem_bloco_de_custos_da_erro_claro():
    arquivo = xlsx({"DRE": [["Descrição", "Valor"], ["(=) RECEITA LIQUIDA", 3200]]})
    with pytest.raises(ErroLeitura, match="CUSTOS"):
        ler_compras(arquivo, PERIODO)


def test_movimento_de_estoque_calcula_custo_e_marca_consumo():
    extracao = ler_planilha(planilha_movimento_xlsx(), PERIODO)

    assert extracao.por_nivel("total")[0].nome == TOTAL_CONSUMO
    assert {g.nome: g.custo for g in extracao.por_nivel("grupo")} == {
        "ALIMENTOS": 330,
        "BEBIDAS": 420,
    }


@pytest.mark.parametrize(
    ("arquivo", "base"),
    [
        (dre_xlsx(), BASE_COMPRAS),
        (dre_sem_codigo_xlsx(), BASE_COMPRAS),
        (planilha_movimento_xlsx(), BASE_CONSUMO),
        (planilha_real_xlsx(), BASE_DECLARADA),
    ],
)
def test_base_do_lado_real_vem_do_formato(arquivo, base):
    total = ler("compras", arquivo, PERIODO).por_nivel("total")[0]
    assert base_do_total(total.nome) == base


# ------------------------------------------------------------------ fechamento
def test_dre_do_everest_nao_e_cmv_real(client, casa_id):
    """Dado o cardápio e a DRE do mês, quando o sócio abre o fechamento, então
    o lado real aparece como compras e o texto não afirma desvio."""
    _enviar(client, casa_id, "cardapio", cardapio_xlsx())
    _enviar(client, casa_id, "compras", dre_xlsx())

    corpo = _fechamento(client, casa_id)

    assert corpo["base_real"] == "compras"
    assert corpo["total"]["ajuste_pp"] == 1.67  # o número continua lá, para conferência
    exp = corpo["explicacao"]
    assert exp["conclusivo"] is False
    assert "ainda não é o CMV real" in exp["resumo"]
    assert "R$ 30 de variação de estoque" in exp["resumo"]  # venda 3000 ÷ 100
    assert any("inventário" in s for s in exp["sugestoes"])


def test_movimento_de_estoque_e_cmv_real_conclusivo(client, casa_id):
    _enviar(client, casa_id, "cardapio", cardapio_xlsx())
    _enviar(client, casa_id, "compras", planilha_movimento_xlsx())

    corpo = _fechamento(client, casa_id)

    assert corpo["base_real"] == "consumo"
    assert corpo["total"]["custo_real"] == 750.0
    assert corpo["explicacao"]["conclusivo"] is True
    assert corpo["acumulado"]["conclusivo"] is True


def test_sem_lado_real_nao_tem_base_nem_acumulado(client, casa_id):
    _enviar(client, casa_id, "cardapio", cardapio_xlsx())

    corpo = _fechamento(client, casa_id)

    assert corpo["base_real"] is None
    assert corpo["acumulado"] is None


# -------------------------------------------------------------------- acumulado
def test_um_mes_so_de_compras_nao_e_conclusivo(client, casa_id):
    _enviar(client, casa_id, "cardapio", cardapio_xlsx())
    _enviar(client, casa_id, "compras", dre_xlsx())

    acumulado = _fechamento(client, casa_id)["acumulado"]

    assert acumulado["meses"] == 1
    assert acumulado["base_real"] == "compras"
    assert acumulado["conclusivo"] is False
    assert acumulado["meses_minimos"] == 6


def test_acumulado_soma_os_meses_e_dilui_o_estoque(client, casa_id):
    """Estoque entrando e saindo deixa o mês isolado oscilar; somado, ALIMENTOS
    bate com o teórico. É o que o acumulado mostra e o mês esconde."""
    meses = [f"2026-0{m}" for m in range(4, 10)]  # abr a set: 6 meses
    for i, periodo in enumerate(meses):
        _enviar(client, casa_id, "cardapio", cardapio_xlsx(), periodo)
        ei, ef = (100, 0) if i % 2 == 0 else (0, 100)  # ALIMENTOS 400, 200, 400…
        _enviar(
            client,
            casa_id,
            "compras",
            planilha_movimento_xlsx(ei_alimentos=ei, ef_alimentos=ef),
            periodo,
        )
    # fora da janela de 12 meses, e um mês com um lado só: nenhum dos dois entra
    _enviar(client, casa_id, "cardapio", cardapio_xlsx(), "2025-01")
    _enviar(client, casa_id, "compras", dre_xlsx(), "2025-01")
    _enviar(client, casa_id, "cardapio", cardapio_xlsx(), "2026-03")

    acumulado = _fechamento(client, casa_id, "2026-09")["acumulado"]

    assert acumulado["periodos"] == meses
    assert acumulado["base_real"] == "consumo"
    assert acumulado["conclusivo"] is True
    total = acumulado["total"]
    assert total["custo_teorico"] == 700.0 * 6
    assert total["custo_real"] == (300 + 420) * 6
    assert total["venda_liquida"] == 3000.0 * 6
    alimentos = {g["grupo"]: g for g in acumulado["grupos"]}["ALIMENTOS"]
    assert alimentos["ajuste_pp"] == 0.0
    assert acumulado["ajuste_mensal_min_pp"] < total["ajuste_pp"]
    assert total["ajuste_pp"] < acumulado["ajuste_mensal_max_pp"]


def test_seis_meses_de_compras_ja_sao_conclusivos(client, casa_id):
    for m in range(4, 10):
        _enviar(client, casa_id, "cardapio", cardapio_xlsx(), f"2026-0{m}")
        _enviar(client, casa_id, "compras", dre_xlsx(), f"2026-0{m}")

    acumulado = _fechamento(client, casa_id)["acumulado"]

    assert acumulado["meses"] == 6
    assert acumulado["base_real"] == "compras"
    assert acumulado["conclusivo"] is True


def test_evolucao_informa_a_base(client, casa_id):
    _enviar(client, casa_id, "cardapio", cardapio_xlsx())
    _enviar(client, casa_id, "compras", dre_xlsx())

    pontos = client.get(EVOLUCAO, params={"casa_id": casa_id}).json()

    assert pontos[-1]["base_real"] == "compras"


# ---------------------------------------------------------------- texto (puro)
def test_texto_de_compras_dentro_da_margem_tambem_nao_conclui():
    total = {"ajuste_pp": 0.5, "ajuste": 15.0, "venda_liquida": 3000.0}
    grupos = [{"grupo": "ALIMENTOS", "ajuste": 15.0}]

    dados = explicacao.explicar(periodo=PERIODO, total=total, grupos=grupos, base_real="compras")

    assert dados["conclusivo"] is False
    assert "perto do CMV previsto" in dados["resumo"]
    assert dados["sugestoes"] == explicacao.SUGESTOES_COMPRAS
