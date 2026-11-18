"""Margem por item: o mesmo item do cardápio em dois meses, ordenado pelo
quanto custou a mais (`app/services/margem.py`).

Os números da API saem do cardápio da casa de demonstração
(`tests/sintetico.py`), em que GIN TONICA, REFRIGERANTE LATA e
PICANHA NA CHAPA têm o custo da ficha subindo mês a mês com o preço parado.
"""

import io

import pytest

from app.services.margem import ItemMes, comparar, escolher_base, resumo
from tests import sintetico

CASAS = "/api/v1/casas"
UPLOADS = "/api/v1/uploads-custo"
FECHAMENTO = "/api/v1/metricas/fechamento"
MARGEM = "/api/v1/metricas/margem-itens"
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


# ------------------------------------------------------------ regra pura
def _item(nome, quantidade, venda, custo, grupo="BEBIDAS"):
    return ItemMes(nome, grupo, None, quantidade, venda, custo)


def test_custo_extra_e_o_custo_acima_da_margem_do_mes_base():
    # CMV 20% → 30% com venda de 2.000: custaria 400, custou 600 → 200 a mais
    base = {"X": _item("X", 100, 1000, 200)}
    atual = {"X": _item("X", 100, 2000, 600)}

    [linha] = comparar(base, atual)

    assert linha["cmv_base_pct"] == 20.0
    assert linha["cmv_atual_pct"] == 30.0
    assert linha["variacao_pp"] == 10.0
    assert linha["custo_extra"] == 200.0
    # preço por unidade 10 → 20 (+100%), custo por unidade 2 → 6 (+200%)
    assert linha["variacao_preco_pct"] == 100.0
    assert linha["variacao_custo_pct"] == 200.0


def test_ordena_pelo_impacto_em_reais_e_nao_pelo_cmv():
    base = {
        "PEQUENO": _item("PEQUENO", 10, 1000, 100),  # 10% → 40%, venda 1.000: +300
        "GRANDE": _item("GRANDE", 10, 50000, 10000),  # 20% → 22%, venda 50.000: +1.000
    }
    atual = {
        "PEQUENO": _item("PEQUENO", 10, 1000, 400),
        "GRANDE": _item("GRANDE", 10, 50000, 11000),
    }

    linhas = comparar(base, atual)

    assert [linha["nome"] for linha in linhas] == ["GRANDE", "PEQUENO"]


def test_item_de_um_mes_so_ou_de_venda_pequena_fica_fora():
    base = {
        "NOVO_NO_BASE": _item("NOVO_NO_BASE", 10, 1000, 100),
        "POUCO": _item("POUCO", 2, 80, 20),
    }
    atual = {"SO_NO_ATUAL": _item("SO_NO_ATUAL", 10, 1000, 100), "POUCO": _item("POUCO", 2, 80, 40)}

    assert comparar(base, atual) == []


def test_resumo_conta_so_quem_passou_do_limiar():
    linhas = [
        {"variacao_pp": 5.0, "custo_extra": 300.0},
        {"variacao_pp": 0.4, "custo_extra": 50.0},  # dentro da margem: não conta
        {"variacao_pp": -3.0, "custo_extra": -200.0},
    ]

    assert resumo(linhas) == {
        "itens_comparados": 3,
        "itens_que_pioraram": 1,
        "custo_extra_total": 300.0,
    }


@pytest.mark.parametrize(
    ("periodos", "esperado"),
    [
        (["2025-09", "2026-04", "2026-08"], ("2025-09", "mesmo mês do ano anterior")),
        (["2026-04", "2026-08"], ("2026-04", "mês mais antigo com dado nos últimos 12 meses")),
        (["2024-01", "2025-02"], ("2025-02", "último mês com dado antes do período")),
        (["2026-09", "2026-10"], None),
    ],
)
def test_escolhe_o_mes_base(periodos, esperado):
    assert escolher_base(periodos, "2026-09") == esperado


# ------------------------------------------------------------------- API
@pytest.fixture
def casa_demo(client) -> int:
    casa = {"nome": "Bar Sintetico (DEMO)", "marca": "Bar Sintetico", "cidade": "Sao Paulo"}
    return client.post(CASAS, json=casa).json()["id"]


def _enviar_cardapio(client, casa_id, periodo):
    resposta = client.post(
        UPLOADS,
        data={"casa_id": casa_id, "periodo": periodo, "tipo": "cardapio"},
        files={"arquivo": ("cardapio.xlsx", io.BytesIO(sintetico.cardapio_xlsx(periodo)), XLSX)},
    )
    assert resposta.status_code == 201, resposta.text


@pytest.fixture
def casa_com_cardapio(client, casa_demo) -> int:
    for periodo in sintetico.PERIODOS:
        _enviar_cardapio(client, casa_demo, periodo)
    return casa_demo


def test_margem_aponta_os_itens_com_custo_subindo(client, casa_com_cardapio):
    resposta = client.get(MARGEM, params={"casa_id": casa_com_cardapio, "periodo": "2026-09"})

    assert resposta.status_code == 200, resposta.text
    dados = resposta.json()
    # sem o mesmo mês do ano anterior, compara com o mais antigo dos 12 meses
    assert dados["periodo_base"] == "2026-04"
    assert dados["itens_comparados"] == 12
    assert dados["itens_que_pioraram"] == 3
    assert dados["custo_extra_total"] > 0
    piores = [item["nome"] for item in dados["items"][:3]]
    assert set(piores) == {"GIN TONICA", "REFRIGERANTE LATA", "PICANHA NA CHAPA"}
    for item in dados["items"][:3]:
        assert item["variacao_custo_pct"] > 10
        assert abs(item["variacao_preco_pct"]) < 1  # preço parado (arredondamento)
        # série do mês-base ao mês, um ponto por mês
        assert [p["periodo"] for p in item["serie"]] == sintetico.PERIODOS


def test_margem_com_mes_base_escolhido(client, casa_com_cardapio):
    params = {"casa_id": casa_com_cardapio, "periodo": "2026-09", "base": "2026-08"}
    dados = client.get(MARGEM, params=params).json()

    assert dados["periodo_base"] == "2026-08"
    assert dados["criterio_base"] == "escolhido"
    assert [p["periodo"] for p in dados["items"][0]["serie"]] == ["2026-08", "2026-09"]


def test_margem_e_paginada(client, casa_com_cardapio):
    params = {"casa_id": casa_com_cardapio, "periodo": "2026-09", "limit": 4, "offset": 8}
    dados = client.get(MARGEM, params=params).json()

    assert dados["total"] == 12
    assert len(dados["items"]) == 4
    # o resumo é do mês inteiro, não da página
    assert dados["itens_que_pioraram"] == 3


def test_margem_casa_inexistente_devolve_404(client):
    assert client.get(MARGEM, params={"casa_id": 999, "periodo": "2026-09"}).status_code == 404


def test_margem_mes_sem_cardapio_devolve_404(client, casa_com_cardapio):
    resposta = client.get(MARGEM, params={"casa_id": casa_com_cardapio, "periodo": "2026-10"})
    assert resposta.status_code == 404
    assert "2026-10" in resposta.json()["detail"]


def test_margem_sem_mes_anterior_devolve_404(client, casa_demo):
    _enviar_cardapio(client, casa_demo, "2026-04")
    resposta = client.get(MARGEM, params={"casa_id": casa_demo, "periodo": "2026-04"})
    assert resposta.status_code == 404


def test_margem_base_igual_ou_posterior_devolve_422(client, casa_com_cardapio):
    params = {"casa_id": casa_com_cardapio, "periodo": "2026-06", "base": "2026-06"}
    assert client.get(MARGEM, params=params).status_code == 422


def test_margem_base_sem_cardapio_devolve_404(client, casa_com_cardapio):
    params = {"casa_id": casa_com_cardapio, "periodo": "2026-09", "base": "2025-09"}
    assert client.get(MARGEM, params=params).status_code == 404


def test_margem_periodo_invalido_devolve_422(client, casa_com_cardapio):
    params = {"casa_id": casa_com_cardapio, "periodo": "09/2026"}
    assert client.get(MARGEM, params=params).status_code == 422
