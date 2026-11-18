"""Engenharia de cardápio (RF16): a matriz popularidade × margem de
Kasavana & Smith, por grupo (`app/services/engenharia.py`).

Os números da API saem do cardápio da casa de demonstração
(`app/services/demo_fechamento.py`), que tem item nos quatro quadrantes dos dois
grupos e a LIMONADA JARRA vendida abaixo do custo.
"""

import io

import pytest

from app.services import demo_fechamento
from app.services.engenharia import abaixo_do_custo, classificar, contagem, fora_da_matriz
from app.services.margem import ItemMes

CASAS = "/api/v1/casas"
UPLOADS = "/api/v1/uploads-custo"
CARDAPIO_DEMO = "/api/v1/modelos/fechamento/demo/cardapio"
ENGENHARIA = "/api/v1/metricas/engenharia-cardapio"
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


# ------------------------------------------------------------ regra pura
def _item(nome, quantidade, venda, custo, grupo="ALIMENTOS"):
    return ItemMes(nome, grupo, None, quantidade, venda, custo)


def test_quatro_quadrantes_com_os_cortes_do_metodo():
    # 4 itens, 100 unidades: popular se >= 0,7/4 = 17,5% das unidades.
    # Margem total = 1900 + 400 + 300 + 50 = 2650 → média 26,50 por unidade.
    itens = [
        _item("ESTRELA", 40, 2400, 500),  # 40% · margem 47,50
        _item("BURRO", 40, 800, 400),  # 40% · margem 10,00
        _item("QUEBRA", 10, 400, 100),  # 10% · margem 30,00
        _item("CAO", 10, 100, 50),  # 10% · margem 5,00
    ]

    cortes, linhas = classificar(itens, venda_minima=0)

    [corte] = cortes
    assert corte.margem_media_unitaria == 26.5
    assert corte.limiar_popularidade_pct == 17.5
    classes = {linha["nome"]: linha["classe"] for linha in linhas}
    assert classes == {
        "ESTRELA": "estrela",
        "BURRO": "burro_de_carga",
        "QUEBRA": "quebra_cabeca",
        "CAO": "cao",
    }
    assert contagem(linhas, "ALIMENTOS") == {
        "estrela": 1,
        "burro_de_carga": 1,
        "quebra_cabeca": 1,
        "cao": 1,
    }


def test_grupos_sao_comparados_separadamente():
    # Sozinha em BEBIDAS, a água é a média do próprio grupo — não é comparada
    # com a margem dos pratos.
    itens = [
        _item("PRATO", 10, 1000, 300),
        _item("AGUA", 100, 600, 100, grupo="BEBIDAS"),
    ]

    cortes, linhas = classificar(itens, venda_minima=0)

    assert [c.grupo for c in cortes] == ["ALIMENTOS", "BEBIDAS"]
    assert {linha["nome"]: linha["classe"] for linha in linhas} == {
        "PRATO": "estrela",
        "AGUA": "estrela",
    }


def test_abaixo_do_custo_olha_todos_os_itens_menos_o_preco_simbolico():
    itens = [
        _item("PRATO", 100, 5000, 1500),  # na matriz, com lucro
        _item("JARRA", 36, 400, 1387),  # venda < R$ 500: fora da matriz, mas perde dinheiro
        _item("CORTESIA", 8, 0.08, 3.47),  # R$ 0,01 por unidade: preço simbólico
    ]
    _, linhas = classificar(itens)

    abaixo = abaixo_do_custo(itens, linhas)

    assert [linha["nome"] for linha in abaixo] == ["JARRA"]
    assert abaixo[0]["margem_unitaria"] == -27.42
    assert abaixo[0]["classe"] is None  # fora da matriz, mas no alerta


def test_matriz_so_com_venda_minima_e_conta_quem_ficou_fora():
    itens = [_item("GRANDE", 100, 5000, 1500), _item("PEQUENO", 2, 80, 20)]

    _, linhas = classificar(itens)

    assert [linha["nome"] for linha in linhas] == ["GRANDE"]
    assert fora_da_matriz(itens, "ALIMENTOS") == 1


def test_item_sem_unidade_ou_sem_venda_fica_fora():
    _, linhas = classificar([_item("OK", 10, 100, 30), _item("CORTESIA", 5, 0, 20)], venda_minima=0)

    assert [linha["nome"] for linha in linhas] == ["OK"]


# ------------------------------------------------------------------- API
@pytest.fixture
def casa_demo(client) -> int:
    casa = {**demo_fechamento.CASA_DEMO, "ativa": True}
    casa_id = client.post(CASAS, json=casa).json()["id"]
    conteudo = client.get(CARDAPIO_DEMO, params={"periodo": "2026-09"}).content
    resposta = client.post(
        UPLOADS,
        data={"casa_id": casa_id, "periodo": "2026-09", "tipo": "cardapio"},
        files={"arquivo": ("cardapio.xlsx", io.BytesIO(conteudo), XLSX)},
    )
    assert resposta.status_code == 201, resposta.text
    return casa_id


def test_demo_tem_os_quatro_quadrantes_nos_dois_grupos(client, casa_demo):
    resposta = client.get(ENGENHARIA, params={"casa_id": casa_demo, "periodo": "2026-09"})

    assert resposta.status_code == 200, resposta.text
    dados = resposta.json()
    assert [g["grupo"] for g in dados["grupos"]] == ["ALIMENTOS", "BEBIDAS"]
    for grupo in dados["grupos"]:
        assert grupo["itens"] == 6
        for classe in ("estrela", "burro_de_carga", "quebra_cabeca", "cao"):
            assert grupo[classe] >= 1, (grupo["grupo"], classe)
    assert [i["nome"] for i in dados["abaixo_do_custo"]] == ["LIMONADA JARRA"]
    assert dados["abaixo_do_custo_total"] == 1
    assert dados["abaixo_do_custo_prejuizo"] < 0
    assert dados["total"] == 12


def test_filtra_por_grupo_e_quadrante(client, casa_demo):
    params = {"casa_id": casa_demo, "periodo": "2026-09", "grupo": "BEBIDAS", "classe": "cao"}
    dados = client.get(ENGENHARIA, params=params).json()

    assert [i["nome"] for i in dados["items"]] == ["LIMONADA JARRA"]
    # o resumo continua sendo do mês inteiro
    assert len(dados["grupos"]) == 2


def test_engenharia_e_paginada(client, casa_demo):
    params = {"casa_id": casa_demo, "periodo": "2026-09", "limit": 5, "offset": 10}
    dados = client.get(ENGENHARIA, params=params).json()

    assert dados["total"] == 12
    assert len(dados["items"]) == 2


def test_engenharia_casa_inexistente_devolve_404(client):
    assert client.get(ENGENHARIA, params={"casa_id": 999, "periodo": "2026-09"}).status_code == 404


def test_engenharia_mes_sem_cardapio_devolve_404(client, casa_demo):
    resposta = client.get(ENGENHARIA, params={"casa_id": casa_demo, "periodo": "2026-08"})
    assert resposta.status_code == 404
    assert "2026-08" in resposta.json()["detail"]


def test_engenharia_grupo_sem_itens_devolve_404(client, casa_demo):
    params = {"casa_id": casa_demo, "periodo": "2026-09", "grupo": "PIZZAS"}
    assert client.get(ENGENHARIA, params=params).status_code == 404


def test_engenharia_classe_invalida_devolve_422(client, casa_demo):
    params = {"casa_id": casa_demo, "periodo": "2026-09", "classe": "unicornio"}
    assert client.get(ENGENHARIA, params=params).status_code == 422


def test_engenharia_periodo_invalido_devolve_422(client, casa_demo):
    params = {"casa_id": casa_demo, "periodo": "09/2026"}
    assert client.get(ENGENHARIA, params=params).status_code == 422


def test_grupo_sem_custo_de_mercadoria_fica_fora(client):
    """SERVICOS (couvert) vem no cardápio sem custo de mercadoria: não entra na
    matriz, como não entra no fechamento."""
    from openpyxl import Workbook

    casa_id = client.post(
        CASAS, json={"nome": "Bar Teste (DEMO)", "marca": "Bar Teste", "cidade": "Sao Paulo"}
    ).json()["id"]
    wb = Workbook()
    ws = wb.active
    ws.append(["grupo", "subgrupo", "item", "quantidade", "venda_liquida", "custo"])
    ws.append(["ALIMENTOS", "PRATOS", "PRATO A", 100, 5000, 1500])
    ws.append(["ALIMENTOS", "PRATOS", "PRATO B", 50, 3000, 1200])
    ws.append(["SERVICOS", "COUVERT", "COUVERT ARTISTICO", 500, 7500, 0])
    arquivo = io.BytesIO()
    wb.save(arquivo)
    resposta = client.post(
        UPLOADS,
        data={"casa_id": casa_id, "periodo": "2026-09", "tipo": "cardapio"},
        files={"arquivo": ("cardapio.xlsx", io.BytesIO(arquivo.getvalue()), XLSX)},
    )
    assert resposta.status_code == 201, resposta.text

    dados = client.get(ENGENHARIA, params={"casa_id": casa_id, "periodo": "2026-09"}).json()

    assert [g["grupo"] for g in dados["grupos"]] == ["ALIMENTOS"]
    assert dados["total"] == 2
