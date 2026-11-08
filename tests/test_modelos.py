"""Planilha-modelo gerada pela API (P0 do ciclo 07/11, docs/11 seção 4.2).

O teste que importa é o do meio: o arquivo baixado é **reenviado** ao endpoint
de upload e precisa ser aceito. Sem ele, o modelo e o leitor descolam em
silêncio — o usuário baixa a planilha indicada pelo sistema e toma 422.
"""

import io

import pytest

MODELOS = "/api/v1/modelos"
CASAS = "/api/v1/casas"
UPLOADS = "/api/v1/uploads-custo"
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
PERIODO = "2026-09"


@pytest.fixture
def casa_id(client, casa_valida) -> int:
    return client.post(CASAS, json=casa_valida).json()["id"]


@pytest.mark.parametrize("tipo", ["cardapio", "compras"])
def test_modelo_e_um_xlsx_para_download(client, tipo):
    resposta = client.get(f"{MODELOS}/{tipo}")

    assert resposta.status_code == 200
    assert resposta.headers["content-type"] == XLSX
    assert f"modelo-{tipo}.xlsx" in resposta.headers["content-disposition"]
    assert resposta.content[:2] == b"PK"  # .xlsx é um zip


@pytest.mark.parametrize("tipo", ["cardapio", "compras"])
def test_modelo_baixado_e_aceito_de_volta_pelo_upload(client, casa_id, tipo):
    modelo = client.get(f"{MODELOS}/{tipo}").content

    resposta = client.post(
        UPLOADS,
        data={"casa_id": casa_id, "periodo": PERIODO, "tipo": tipo},
        files={"arquivo": (f"modelo-{tipo}.xlsx", io.BytesIO(modelo), XLSX)},
    )

    assert resposta.status_code == 201, resposta.text
    # 1 total + 2 grupos + os subgrupos de cada lado (+ os itens, no cardápio)
    assert resposta.json()["linhas_importadas"] >= 5


def test_modelo_do_cardapio_tem_as_colunas_do_contrato_de_entrada(client, casa_id):
    """Tabela C de `docs/07-fechamento-cmv.md`: sem `venda_liquida` no lado
    teórico não existe CMV %, e sem `quantidade` não existe "Quanto comprar"."""
    modelo = client.get(f"{MODELOS}/cardapio").content
    client.post(
        UPLOADS,
        data={"casa_id": casa_id, "periodo": PERIODO, "tipo": "cardapio"},
        files={"arquivo": ("modelo.xlsx", io.BytesIO(modelo), XLSX)},
    )

    fechamento = client.get(
        "/api/v1/metricas/fechamento", params={"casa_id": casa_id, "periodo": PERIODO}
    ).json()
    recomendacao = client.get(
        "/api/v1/metricas/recomendacao-compra", params={"casa_id": casa_id, "periodo": PERIODO}
    )

    assert fechamento["total"]["venda_liquida"] == 21200.0
    assert fechamento["total"]["cmv_teorico_pct"] is not None
    assert recomendacao.status_code == 200


def test_tipo_invalido_devolve_422(client):
    assert client.get(f"{MODELOS}/dre").status_code == 422
