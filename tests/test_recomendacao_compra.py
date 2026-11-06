"""Endpoint de recomendação de compra (RF07).

A matemática está coberta em `test_previsao.py`, sem banco. Aqui testamos o que
só aparece pela API: a leitura do histórico no banco, a montagem da série por
item, os erros e — o mais importante — se a resposta carrega o aviso sobre o
limite do cálculo. Número de compra sem a ressalva de que ele ignora o estoque
atual é número que faz alguém comprar errado.
"""

import io

from tests.planilhas import cardapio_xlsx, planilha_item_xlsx

CASAS = "/api/v1/casas"
UPLOADS = "/api/v1/uploads-custo"
RECOMENDACAO = "/api/v1/metricas/recomendacao-compra"
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _casa(client) -> int:
    dados = {"nome": "Boteco São Bento - Vila Madalena", "marca": "Boteco São Bento",
             "cidade": "São Paulo"}  # fmt: skip
    return client.post(CASAS, json=dados).json()["id"]


def _upload(client, casa_id: int, periodo: str, conteudo: bytes) -> None:
    resposta = client.post(
        UPLOADS,
        data={"casa_id": casa_id, "periodo": periodo, "tipo": "cardapio"},
        files={"arquivo": ("export.xlsx", io.BytesIO(conteudo), XLSX)},
    )
    assert resposta.status_code == 201, resposta.text


def _enviar_cardapio(client, casa_id: int, periodo: str, fator: float = 1.0) -> None:
    _upload(client, casa_id, periodo, cardapio_xlsx(fator=fator))


def _enviar_quantidade(client, casa_id: int, periodo: str, quantidade: float) -> None:
    """Histórico com quantidade controlada, via planilha genérica."""
    _upload(client, casa_id, periodo, planilha_item_xlsx(quantidade=quantidade))


def test_recomendacao_usa_o_historico_e_preve_o_mes_seguinte(client):
    casa_id = _casa(client)
    # BOLINHO vende 10 unidades por mês na planilha sintética (fator 1,0)
    for periodo in ("2026-06", "2026-07", "2026-08"):
        _enviar_cardapio(client, casa_id, periodo)

    corpo = client.get(
        RECOMENDACAO, params={"casa_id": casa_id, "periodo": "2026-08", "margem_seguranca_pct": 0}
    ).json()

    assert corpo["periodo_base"] == "2026-08"
    assert corpo["periodo_alvo"] == "2026-09"

    itens = {i["nome"]: i for i in corpo["itens"]}
    assert "BOLINHO" in itens
    bolinho = itens["BOLINHO"]
    assert bolinho["meses_com_dado"] == 3
    assert bolinho["media_recente"] == 10.0
    assert bolinho["demanda_prevista"] == 10.0  # venda estável
    assert bolinho["grupo"] == "ALIMENTOS"
    assert [p["periodo"] for p in bolinho["historico"]] == ["2026-06", "2026-07", "2026-08"]


def test_resposta_declara_o_metodo_e_o_limite_do_calculo(client):
    casa_id = _casa(client)
    _enviar_cardapio(client, casa_id, "2026-08")

    corpo = client.get(RECOMENDACAO, params={"casa_id": casa_id, "periodo": "2026-08"}).json()

    # Não vender como IA o que é média móvel
    assert "machine learning" in corpo["metodo"].lower()
    # E dizer, junto do número, que ele ignora o estoque atual
    assert "estoque" in corpo["aviso"].lower()


def test_margem_de_seguranca_aparece_so_na_sugestao(client):
    casa_id = _casa(client)
    for periodo in ("2026-07", "2026-08"):
        _enviar_cardapio(client, casa_id, periodo)

    corpo = client.get(
        RECOMENDACAO, params={"casa_id": casa_id, "periodo": "2026-08", "margem_seguranca_pct": 25}
    ).json()

    bolinho = next(i for i in corpo["itens"] if i["nome"] == "BOLINHO")
    assert bolinho["demanda_prevista"] == 10.0
    assert bolinho["sugestao_compra"] == 12.5


def test_venda_crescente_eleva_a_previsao(client):
    casa_id = _casa(client)
    # 3 meses vendendo 10/mês, depois 3 meses vendendo 20/mês
    for periodo, qtd in [
        ("2026-03", 10), ("2026-04", 10), ("2026-05", 10),
        ("2026-06", 20), ("2026-07", 20), ("2026-08", 20),
    ]:  # fmt: skip
        _enviar_quantidade(client, casa_id, periodo, qtd)

    corpo = client.get(
        RECOMENDACAO, params={"casa_id": casa_id, "periodo": "2026-08", "margem_seguranca_pct": 0}
    ).json()

    bolinho = next(i for i in corpo["itens"] if i["nome"] == "BOLINHO")
    assert bolinho["media_recente"] == 20.0
    assert bolinho["tendencia_pct"] == 50.0  # travado no limite (dobrou = +100%)
    assert bolinho["demanda_prevista"] == 30.0  # 20 × 1,5


def test_venda_em_queda_reduz_a_previsao(client):
    casa_id = _casa(client)
    for periodo, qtd in [
        ("2026-03", 100), ("2026-04", 100), ("2026-05", 100),
        ("2026-06", 80), ("2026-07", 80), ("2026-08", 80),
    ]:  # fmt: skip
        _enviar_quantidade(client, casa_id, periodo, qtd)

    corpo = client.get(
        RECOMENDACAO, params={"casa_id": casa_id, "periodo": "2026-08", "margem_seguranca_pct": 0}
    ).json()

    bolinho = next(i for i in corpo["itens"] if i["nome"] == "BOLINHO")
    assert bolinho["tendencia_pct"] == -20.0
    assert bolinho["demanda_prevista"] == 64.0  # 80 × 0,80


def test_limit_controla_quantos_itens_voltam(client):
    casa_id = _casa(client)
    _enviar_cardapio(client, casa_id, "2026-08")

    corpo = client.get(
        RECOMENDACAO, params={"casa_id": casa_id, "periodo": "2026-08", "limit": 1}
    ).json()

    assert len(corpo["itens"]) == 1


def test_casa_sem_cardapio_devolve_404_dizendo_o_que_falta(client):
    casa_id = _casa(client)

    resposta = client.get(RECOMENDACAO, params={"casa_id": casa_id, "periodo": "2026-08"})

    assert resposta.status_code == 404
    assert "cardápio" in resposta.json()["detail"]


def test_casa_inexistente_devolve_404(client):
    assert (
        client.get(RECOMENDACAO, params={"casa_id": 999, "periodo": "2026-08"}).status_code == 404
    )


def test_periodo_invalido_devolve_422(client):
    casa_id = _casa(client)

    resposta = client.get(RECOMENDACAO, params={"casa_id": casa_id, "periodo": "ago/26"})

    assert resposta.status_code == 422


def test_margem_fora_do_intervalo_devolve_422(client):
    casa_id = _casa(client)

    resposta = client.get(
        RECOMENDACAO,
        params={"casa_id": casa_id, "periodo": "2026-08", "margem_seguranca_pct": 500},
    )

    assert resposta.status_code == 422


def test_historico_nao_inclui_meses_posteriores_ao_periodo(client):
    """Prever 2026-07 não pode usar a venda de 2026-08 — seria olhar o futuro,
    e a previsão pareceria boa num teste e falharia na vida real."""
    casa_id = _casa(client)
    _enviar_quantidade(client, casa_id, "2026-06", 10)
    _enviar_quantidade(client, casa_id, "2026-07", 10)
    _enviar_quantidade(client, casa_id, "2026-08", 500)  # mês que não deve ser visto

    corpo = client.get(
        RECOMENDACAO, params={"casa_id": casa_id, "periodo": "2026-07", "margem_seguranca_pct": 0}
    ).json()

    bolinho = next(i for i in corpo["itens"] if i["nome"] == "BOLINHO")
    assert bolinho["meses_com_dado"] == 2
    assert [p["periodo"] for p in bolinho["historico"]] == ["2026-06", "2026-07"]
    assert bolinho["demanda_prevista"] == 10.0  # sem contaminação dos 500 de agosto
