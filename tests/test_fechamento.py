"""Fechamento de CMV (RF02/RF04): teórico × real × ajuste, evolução e top itens.

Números esperados saem de tests/planilhas.py:
  ALIMENTOS: teórico 300, real 330, venda 1000 → 30% × 33%, ajuste +30 / +3 pp
  BEBIDAS:   teórico 400, real 420, venda 2000 → 20% × 21%, ajuste +20 / +1 pp
  TOTAL:     teórico 700, real 750, venda 3000 → 23,33% × 25%, ajuste +50 / +1,67 pp
"""

import io

import pytest

from tests.planilhas import cardapio_xlsx, dre_xlsx

CASAS = "/api/v1/casas"
UPLOADS = "/api/v1/uploads-custo"
FECHAMENTO = "/api/v1/metricas/fechamento"
EVOLUCAO = "/api/v1/metricas/evolucao"
TOP = "/api/v1/metricas/top-itens"
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
PERIODO = "2026-09"


@pytest.fixture
def casa_id(client) -> int:
    casa = {"nome": "Boteco São Bento - Vila Madalena", "marca": "Boteco São Bento",
            "cidade": "São Paulo"}  # fmt: skip
    return client.post(CASAS, json=casa).json()["id"]


def _enviar(client, casa_id, tipo, conteudo, periodo=PERIODO):
    resposta = client.post(
        UPLOADS,
        data={"casa_id": casa_id, "periodo": periodo, "tipo": tipo},
        files={"arquivo": ("export.xlsx", io.BytesIO(conteudo), XLSX)},
    )
    assert resposta.status_code == 201, resposta.text


def test_fechamento_completo_calcula_teorico_real_e_ajuste(client, casa_id):
    _enviar(client, casa_id, "cardapio", cardapio_xlsx())
    _enviar(client, casa_id, "compras", dre_xlsx())

    resposta = client.get(FECHAMENTO, params={"casa_id": casa_id, "periodo": PERIODO})

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["tem_cardapio"] and corpo["tem_compras"]

    grupos = {g["grupo"]: g for g in corpo["grupos"]}
    assert grupos["ALIMENTOS"]["cmv_teorico_pct"] == 30.0
    assert grupos["ALIMENTOS"]["cmv_real_pct"] == 33.0
    assert grupos["ALIMENTOS"]["ajuste"] == 30.0
    assert grupos["ALIMENTOS"]["ajuste_pp"] == 3.0
    assert grupos["BEBIDAS"]["ajuste_pp"] == 1.0

    total = corpo["total"]
    assert total["custo_teorico"] == 700.0
    assert total["custo_real"] == 750.0  # material de consumo (250) fica de fora
    assert total["venda_liquida"] == 3000.0
    assert total["cmv_teorico_pct"] == 23.33
    assert total["cmv_real_pct"] == 25.0
    assert total["ajuste"] == 50.0


def test_fechamento_so_com_cardapio_mostra_teorico_e_real_nulo(client, casa_id):
    _enviar(client, casa_id, "cardapio", cardapio_xlsx())

    corpo = client.get(FECHAMENTO, params={"casa_id": casa_id, "periodo": PERIODO}).json()

    assert corpo["tem_cardapio"] is True
    assert corpo["tem_compras"] is False
    assert corpo["total"]["cmv_teorico_pct"] == 23.33
    assert corpo["total"]["custo_real"] is None
    assert corpo["total"]["ajuste"] is None


def test_fechamento_so_com_compras_usa_receita_da_dre(client, casa_id):
    _enviar(client, casa_id, "compras", dre_xlsx())

    corpo = client.get(FECHAMENTO, params={"casa_id": casa_id, "periodo": PERIODO}).json()

    assert corpo["tem_cardapio"] is False
    assert corpo["total"]["custo_real"] == 750.0
    assert corpo["total"]["cmv_real_pct"] == round(750 / 3200 * 100, 2)


def test_fechamento_sem_upload_no_periodo_devolve_404(client, casa_id):
    _enviar(client, casa_id, "cardapio", cardapio_xlsx())

    resposta = client.get(FECHAMENTO, params={"casa_id": casa_id, "periodo": "2026-01"})

    assert resposta.status_code == 404
    assert "2026-01" in resposta.json()["detail"]


def test_fechamento_casa_inexistente_devolve_404(client):
    assert client.get(FECHAMENTO, params={"casa_id": 999, "periodo": PERIODO}).status_code == 404


def test_fechamento_periodo_invalido_devolve_422(client, casa_id):
    resposta = client.get(FECHAMENTO, params={"casa_id": casa_id, "periodo": "set/26"})
    assert resposta.status_code == 422


def test_evolucao_ordena_meses_cronologicamente(client, casa_id):
    _enviar(client, casa_id, "cardapio", cardapio_xlsx(), periodo="2026-09")
    _enviar(client, casa_id, "cardapio", cardapio_xlsx(), periodo="2026-07")
    _enviar(client, casa_id, "compras", dre_xlsx(), periodo="2026-09")

    pontos = client.get(EVOLUCAO, params={"casa_id": casa_id}).json()

    assert [p["periodo"] for p in pontos] == ["2026-07", "2026-09"]
    assert pontos[0]["cmv_real_pct"] is None
    assert pontos[1]["cmv_real_pct"] == 25.0


def test_evolucao_respeita_limit(client, casa_id):
    for mes in ("2026-07", "2026-08", "2026-09"):
        _enviar(client, casa_id, "cardapio", cardapio_xlsx(), periodo=mes)

    pontos = client.get(EVOLUCAO, params={"casa_id": casa_id, "limit": 2}).json()

    assert [p["periodo"] for p in pontos] == ["2026-08", "2026-09"]


def test_evolucao_sem_dado_devolve_lista_vazia(client, casa_id):
    assert client.get(EVOLUCAO, params={"casa_id": casa_id}).json() == []


def test_top_itens_por_custo_e_por_cmv(client, casa_id):
    _enviar(client, casa_id, "cardapio", cardapio_xlsx())

    por_custo = client.get(TOP, params={"casa_id": casa_id, "periodo": PERIODO}).json()
    por_cmv = client.get(
        TOP, params={"casa_id": casa_id, "periodo": PERIODO, "ordem": "cmv"}
    ).json()

    assert por_custo[0]["nome"] == "CHOPP 300ML"  # maior custo total (400)
    assert por_cmv[0]["nome"] == "BOLINHO"  # 200/600 = 33,33%, maior custo ÷ venda
    assert por_cmv[0]["cmv_pct"] == 33.33


def test_top_itens_ordem_invalida_devolve_422(client, casa_id):
    resposta = client.get(TOP, params={"casa_id": casa_id, "periodo": PERIODO, "ordem": "x"})
    assert resposta.status_code == 422
