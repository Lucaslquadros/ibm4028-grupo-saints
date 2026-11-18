"""Casa de demonstração (`app/services/demo_fechamento.py`).

Em produção ela recebe o cardápio REAL do São Bento, copiado pela API por
`scripts/popular_demo_fechamento.py`. Aqui ela recebe o cardápio sintético de
`tests/sintetico.py`, e o que se confere é a regra: a planilha da demonstração
soma o cardápio do banco por grupo e simula estoque e compras de modo que o
histórico fica dentro da margem e o mês ao vivo fecha acima, puxado por
BEBIDAS, com as compras de bebidas ABAIXO do teórico.
"""

import io

import pytest
from openpyxl import load_workbook

from app.services import demo_fechamento
from tests import sintetico

CASAS = "/api/v1/casas"
UPLOADS = "/api/v1/uploads-custo"
FECHAMENTOS = "/api/v1/fechamentos"
INFO = "/api/v1/modelos/fechamento/demo"
PLANILHA = "/api/v1/modelos/fechamento/demo/planilha"
CARDAPIO = "/api/v1/modelos/fechamento/demo/cardapio"
FECHAMENTO = "/api/v1/metricas/fechamento"
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
AO_VIVO = sintetico.PERIODOS[-1]


def _enviar_cardapio(client, casa_id, periodo):
    resposta = client.post(
        UPLOADS,
        data={"casa_id": casa_id, "periodo": periodo, "tipo": "cardapio"},
        files={"arquivo": ("cardapio.xlsx", io.BytesIO(sintetico.cardapio_xlsx(periodo)), XLSX)},
    )
    assert resposta.status_code == 201, resposta.text


def _enviar_planilha(client, casa_id, conteudo):
    return client.post(
        FECHAMENTOS,
        data={"casa_id": casa_id},
        files={"arquivo": ("demo.xlsx", io.BytesIO(conteudo), XLSX)},
    )


@pytest.fixture
def casa_demo(client) -> int:
    """Como o script deixa a casa: o cardápio de todos os meses, sem planilha."""
    casa_id = client.post(CASAS, json={**demo_fechamento.CASA_DEMO, "ativa": True}).json()["id"]
    for periodo in sintetico.PERIODOS:
        _enviar_cardapio(client, casa_id, periodo)
    return casa_id


def _carregar_historico(client, casa_id):
    info = client.get(INFO).json()
    planilha = client.get(PLANILHA, params={"periodo": info["periodos_historico"]}).content
    resposta = _enviar_planilha(client, casa_id, planilha)
    assert resposta.status_code == 201, resposta.text


def _fechamento(client, casa_id, periodo):
    resposta = client.get(FECHAMENTO, params={"casa_id": casa_id, "periodo": periodo})
    assert resposta.status_code == 200, resposta.text
    return resposta.json()


# ------------------------------------------------------- sem preparo
@pytest.mark.parametrize("rota", [INFO, PLANILHA, CARDAPIO])
def test_sem_casa_de_demo_preparada_devolve_404(client, rota):
    resposta = client.get(rota)
    assert resposta.status_code == 404
    assert "popular_demo_fechamento" in resposta.json()["detail"]


# ------------------------------------------------- com a casa preparada
def test_info_lista_os_meses_do_cardapio(client, casa_demo):
    info = client.get(INFO).json()

    assert info["casa_nome"] == demo_fechamento.CASA_DEMO["nome"]
    assert "(DEMO)" in info["casa_nome"]
    assert info["periodos"] == sintetico.PERIODOS
    assert info["periodo_ao_vivo"] == AO_VIVO
    assert info["periodos_historico"] == sintetico.PERIODOS[:-1]


def test_planilha_soma_o_cardapio_por_grupo(client, casa_demo):
    conteudo = client.get(PLANILHA).content
    linhas = list(load_workbook(io.BytesIO(conteudo))["Fechamento"].iter_rows(values_only=True))

    dados = [linha for linha in linhas[1:] if linha[0]]
    assert {linha[0] for linha in dados} == {AO_VIVO}
    esperado = {g: (v, t) for p, g, v, t, *_ in sintetico.LINHAS if p == AO_VIVO}
    for _periodo, grupo, venda, teorico, *_resto in dados:
        assert venda == pytest.approx(esperado[grupo][0], abs=0.02)
        assert teorico == pytest.approx(esperado[grupo][1], abs=0.02)


def test_mes_fora_da_demo_devolve_422(client, casa_demo):
    assert client.get(PLANILHA, params={"periodo": "2030-01"}).status_code == 422
    assert client.get(CARDAPIO, params={"periodo": "2030-01"}).status_code == 422


def test_mes_ao_vivo_sem_o_historico_e_recusado(client, casa_demo):
    # sem o mês anterior não há estoque inicial: o leitor recusa
    resposta = _enviar_planilha(client, casa_demo, client.get(PLANILHA).content)
    assert resposta.status_code == 422


def test_historico_fica_dentro_da_margem(client, casa_demo):
    _carregar_historico(client, casa_demo)

    for periodo in sintetico.PERIODOS[:-1]:
        fechamento = _fechamento(client, casa_demo, periodo)
        assert fechamento["base_real"] == "consumo"
        assert fechamento["explicacao"]["situacao"] == "dentro", periodo


def test_envio_ao_vivo_fecha_acima_puxado_por_bebidas(client, casa_demo):
    _carregar_historico(client, casa_demo)
    resposta = _enviar_planilha(client, casa_demo, client.get(PLANILHA).content)
    assert resposta.status_code == 201, resposta.text

    fechamento = _fechamento(client, casa_demo, AO_VIVO)

    assert fechamento["explicacao"]["situacao"] == "acima"
    assert fechamento["total"]["ajuste_pp"] > 1
    bebidas = next(g for g in fechamento["grupos"] if g["grupo"] == "BEBIDAS")
    alimentos = next(g for g in fechamento["grupos"] if g["grupo"] == "ALIMENTOS")
    assert bebidas["ajuste_pp"] > alimentos["ajuste_pp"]
    assert "BEBIDAS" in fechamento["explicacao"]["resumo"]


def test_cardapio_da_demo_e_o_do_banco_e_nao_serve_como_planilha(client, casa_demo):
    conteudo = client.get(CARDAPIO).content
    linhas = list(load_workbook(io.BytesIO(conteudo)).active.iter_rows(values_only=True))

    assert len(linhas) - 1 == len(sintetico.cardapio(AO_VIVO))
    # o erro proposital do roteiro: cardápio enviado como planilha de fechamento
    resposta = _enviar_planilha(client, casa_demo, conteudo)
    assert resposta.status_code == 422
    assert "planilha-modelo" in resposta.json()["detail"]


# ------------------------------------------------------- regra pura
def _totais():
    totais: dict = {}
    for periodo, grupo, venda, teorico, *_ in sintetico.LINHAS:
        totais.setdefault(periodo, {})[grupo] = (venda, teorico)
    return totais


def test_compras_de_bebidas_no_mes_ao_vivo_ficam_abaixo_do_teorico():
    """O ponto da demo: o CMV real sobe, mas a DRE de compras diria o contrário."""
    linhas = demo_fechamento.simular(_totais())
    bebidas = next(linha for linha in linhas if linha[0] == AO_VIVO and linha[1] == "BEBIDAS")

    _periodo, _grupo, _venda, teorico, _inicial, compras, _final = bebidas
    assert compras < teorico


def test_so_o_primeiro_mes_tem_estoque_inicial():
    linhas = demo_fechamento.simular(_totais())

    for periodo, _grupo, _v, _t, inicial, *_ in linhas:
        if periodo == sintetico.PERIODOS[0]:
            assert inicial is not None
        else:
            assert inicial is None


def test_simulacao_e_deterministica():
    assert demo_fechamento.simular(_totais()) == demo_fechamento.simular(_totais())
