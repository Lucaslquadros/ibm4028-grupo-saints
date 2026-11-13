"""Casa de demonstração da planilha de fechamento (`app/services/demo_fechamento.py`).

O que a apresentação precisa que seja verdade: o histórico carrega, a planilha
do mês ao vivo que a tela oferece é aceita em cima dele, e o resultado é o que
o roteiro vai dizer (set/26 acima do previsto, puxado por BEBIDAS).
"""

import io

import pytest
from openpyxl import load_workbook

from app.services import demo_fechamento

CASAS = "/api/v1/casas"
FECHAMENTOS = "/api/v1/fechamentos"
INFO = "/api/v1/modelos/fechamento/demo"
PLANILHA = "/api/v1/modelos/fechamento/demo/planilha"
FECHAMENTO = "/api/v1/metricas/fechamento"
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@pytest.fixture
def casa_demo(client) -> int:
    casa = {**demo_fechamento.CASA_DEMO, "ativa": True}
    return client.post(CASAS, json=casa).json()["id"]


def _enviar(client, casa_id, conteudo):
    return client.post(
        FECHAMENTOS,
        data={"casa_id": casa_id},
        files={"arquivo": ("demo.xlsx", io.BytesIO(conteudo), XLSX)},
    )


def _carregar_historico(client, casa_id):
    info = client.get(INFO).json()
    planilha = client.get(PLANILHA, params={"periodo": info["periodos_historico"]}).content
    resposta = _enviar(client, casa_id, planilha)
    assert resposta.status_code == 201, resposta.text


def _fechamento(client, casa_id, periodo):
    resposta = client.get(FECHAMENTO, params={"casa_id": casa_id, "periodo": periodo})
    assert resposta.status_code == 200, resposta.text
    return resposta.json()


def test_info_da_demo(client):
    info = client.get(INFO).json()

    assert "(DEMO)" in info["casa_nome"]
    assert info["periodo_ao_vivo"] == "2026-09"
    assert info["periodos_historico"] == ["2026-04", "2026-05", "2026-06", "2026-07", "2026-08"]
    assert info["periodo_ao_vivo"] not in info["periodos_historico"]


def test_planilha_padrao_e_so_o_mes_ao_vivo(client):
    resposta = client.get(PLANILHA)

    assert resposta.status_code == 200
    assert "demo-fechamento-2026-09.xlsx" in resposta.headers["content-disposition"]
    aba = load_workbook(io.BytesIO(resposta.content))["Fechamento"]
    linhas = [r for r in aba.iter_rows(min_row=2, values_only=True) if r[0]]
    assert [(r[0], r[1]) for r in linhas] == [("2026-09", "ALIMENTOS"), ("2026-09", "BEBIDAS")]
    # estoque_inicial em branco: vem do estoque_final de agosto, já carregado
    assert all(r[4] is None for r in linhas)


def test_mes_fora_da_demo_devolve_422(client):
    resposta = client.get(PLANILHA, params={"periodo": "2025-01"})

    assert resposta.status_code == 422
    assert "2025-01" in resposta.json()["detail"]


def test_mes_ao_vivo_sem_o_historico_e_recusado(client, casa_demo):
    """Se o script de preparo não rodou, o envio ao vivo falha — e a mensagem
    diz por quê. É o que o checklist de véspera precisa pegar."""
    resposta = _enviar(client, casa_demo, client.get(PLANILHA).content)

    assert resposta.status_code == 422
    assert "estoque_inicial" in resposta.json()["detail"]


def test_historico_fica_dentro_da_margem(client, casa_demo):
    _carregar_historico(client, casa_demo)

    for periodo in demo_fechamento.PERIODOS_HISTORICO:
        fechamento = _fechamento(client, casa_demo, periodo)
        assert fechamento["explicacao"]["situacao"] == "dentro", periodo

    resposta = client.get(FECHAMENTO, params={"casa_id": casa_demo, "periodo": "2026-09"})
    assert resposta.status_code == 404  # set/26 ainda não foi enviado


def test_envio_ao_vivo_fecha_setembro_acima_puxado_por_bebidas(client, casa_demo):
    _carregar_historico(client, casa_demo)

    resposta = _enviar(client, casa_demo, client.get(PLANILHA).content)

    assert resposta.status_code == 201, resposta.text
    assert resposta.json()["periodos"] == ["2026-09"]
    setembro = _fechamento(client, casa_demo, "2026-09")
    assert setembro["base_real"] == "consumo"
    assert setembro["total"]["ajuste"] == 8780
    assert setembro["total"]["ajuste_pp"] == 1.61
    assert setembro["explicacao"]["situacao"] == "acima"
    assert "BEBIDAS" in setembro["explicacao"]["resumo"]
    bebidas = {g["grupo"]: g for g in setembro["grupos"]}["BEBIDAS"]
    # EI 104.000 (EF de agosto) + compras 70.800 − EF 92.000
    assert bebidas["custo_real"] == 82800
    assert bebidas["ajuste_pp"] == 2.6
    assert setembro["acumulado"]["meses"] == 6


def test_compras_de_bebidas_em_setembro_ficam_abaixo_do_teorico():
    """O ponto da demo: quem olhasse só compras concluiria o contrário."""
    (_, _, venda, teorico, _, compras, _) = next(
        linha for linha in demo_fechamento.LINHAS if linha[0] == "2026-09" and linha[1] == "BEBIDAS"
    )
    assert compras < teorico
    assert round((compras - teorico) / venda * 100, 2) == -1.4


def test_so_o_primeiro_mes_tem_estoque_inicial():
    primeiro = demo_fechamento.PERIODOS[0]
    for periodo, grupo, *_resto, ei, _compras, _ef in demo_fechamento.LINHAS:
        assert (ei is not None) == (periodo == primeiro), (periodo, grupo)
