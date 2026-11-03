"""Upload dos exports do Everest (RF01).

Rodam no modo local do storage (sem connection string do Azure), então não
dependem de credencial nem de rede. As planilhas são sintéticas (tests/planilhas.py).
"""

import io

from tests.planilhas import cardapio_xlsx, dre_xlsx

CASAS = "/api/v1/casas"
UPLOADS = "/api/v1/uploads-custo"
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
PERIODO = "2026-09"


def _arquivo(conteudo: bytes, nome: str = "export.xlsx", tipo: str = XLSX) -> tuple:
    return (nome, io.BytesIO(conteudo), tipo)


def _criar_casa(client) -> int:
    casa = {"nome": "Boteco São Bento - Vila Madalena", "marca": "Boteco São Bento",
            "cidade": "São Paulo"}  # fmt: skip
    return client.post(CASAS, json=casa).json()["id"]


def _enviar(client, casa_id, tipo="cardapio", conteudo=None, periodo=PERIODO, arquivo=None):
    if arquivo is None:
        arquivo = _arquivo(conteudo if conteudo is not None else cardapio_xlsx())
    return client.post(
        UPLOADS,
        data={"casa_id": casa_id, "periodo": periodo, "tipo": tipo},
        files={"arquivo": arquivo},
    )


def test_upload_cardapio_devolve_201_com_linhas_importadas(client):
    casa_id = _criar_casa(client)

    resposta = _enviar(client, casa_id, "cardapio")

    assert resposta.status_code == 201
    corpo = resposta.json()
    assert corpo["tipo"] == "cardapio"
    assert corpo["linhas_importadas"] > 0
    assert corpo["substituiu_anterior"] is False


def test_upload_compras_devolve_201(client):
    casa_id = _criar_casa(client)

    resposta = _enviar(client, casa_id, "compras", dre_xlsx())

    assert resposta.status_code == 201
    assert resposta.json()["tipo"] == "compras"


def test_reenviar_mesmo_tipo_e_periodo_substitui_o_anterior(client):
    casa_id = _criar_casa(client)
    _enviar(client, casa_id, "cardapio")

    segunda = _enviar(client, casa_id, "cardapio", cardapio_xlsx(fator=2))

    assert segunda.status_code == 201
    assert segunda.json()["substituiu_anterior"] is True
    assert client.get(UPLOADS, params={"casa_id": casa_id}).json()["total"] == 1


def test_blob_name_nao_reusa_o_nome_enviado(client):
    casa_id = _criar_casa(client)

    corpo = _enviar(client, casa_id).json()

    assert corpo["blob_name"] != "export.xlsx"
    assert corpo["blob_name"].endswith(".xlsx")
    assert "/" not in corpo["blob_name"] and ".." not in corpo["blob_name"]


def test_arquivo_do_tipo_errado_devolve_422_com_mensagem_clara(client):
    casa_id = _criar_casa(client)

    resposta = _enviar(client, casa_id, "compras", cardapio_xlsx())

    assert resposta.status_code == 422
    assert "DRE" in resposta.json()["detail"]


def test_upload_para_casa_inexistente_devolve_404(client):
    assert _enviar(client, 999).status_code == 404


def test_csv_ou_outro_formato_devolve_415(client):
    casa_id = _criar_casa(client)
    arquivo = _arquivo(b"item,custo\nX,1\n", nome="export.csv", tipo="text/csv")

    assert _enviar(client, casa_id, arquivo=arquivo).status_code == 415


def test_xlsx_enviado_como_octet_stream_e_aceito(client):
    casa_id = _criar_casa(client)
    arquivo = _arquivo(cardapio_xlsx(), tipo="application/octet-stream")

    assert _enviar(client, casa_id, arquivo=arquivo).status_code == 201


def test_conteudo_que_nao_e_planilha_devolve_422(client):
    casa_id = _criar_casa(client)

    resposta = _enviar(client, casa_id, conteudo=b"MZ... nao e xlsx")

    assert resposta.status_code == 422


def test_arquivo_vazio_devolve_422(client):
    casa_id = _criar_casa(client)
    assert _enviar(client, casa_id, conteudo=b"").status_code == 422


def test_tipo_de_relatorio_invalido_devolve_422(client):
    casa_id = _criar_casa(client)
    assert _enviar(client, casa_id, tipo="estoque").status_code == 422


def test_arquivo_grande_demais_devolve_413(client):
    from app.config import settings

    casa_id = _criar_casa(client)
    excesso = b"x" * (settings.max_upload_mb * 1024 * 1024 + 1)

    assert _enviar(client, casa_id, conteudo=excesso).status_code == 413


def test_periodo_mal_formatado_devolve_422(client):
    casa_id = _criar_casa(client)
    assert _enviar(client, casa_id, periodo="09/2026").status_code == 422


def test_listar_uploads_paginado_e_filtrado(client):
    casa_id = _criar_casa(client)
    _enviar(client, casa_id, "cardapio")
    _enviar(client, casa_id, "compras", dre_xlsx())
    _enviar(client, casa_id, "cardapio", periodo="2026-08")

    todos = client.get(UPLOADS, params={"casa_id": casa_id, "limit": 2}).json()
    setembro = client.get(UPLOADS, params={"casa_id": casa_id, "periodo": PERIODO}).json()

    assert todos["total"] == 3
    assert len(todos["items"]) == 2
    assert setembro["total"] == 2
    assert all(u["linhas_importadas"] > 0 for u in setembro["items"])
