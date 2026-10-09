"""Upload do export de custo (RF01) e delta custo teórico x real (RF02).

Os testes de upload rodam no modo local do storage (sem connection string do
Azure), então não dependem de credencial nem de rede.
"""

import io

CASAS = "/api/v1/casas"
UPLOADS = "/api/v1/uploads-custo"
DELTA = "/api/v1/metricas/delta"

PERIODO = "2026-09"


def _csv(conteudo: str | None = None) -> tuple:
    if conteudo is None:
        conteudo = "item,custo_teorico,custo_real\nGrey Goose,100,120\nChopp,50,45\n"
    return ("export.csv", io.BytesIO(conteudo.encode()), "text/csv")


def _criar_casa(client) -> int:
    casa = {"nome": "Boteco São Bento - Itaim", "marca": "Boteco São Bento", "cidade": "São Paulo"}
    return client.post(CASAS, json=casa).json()["id"]


# ---------------------------------------------------------------- Upload
def test_upload_csv_devolve_201(client):
    casa_id = _criar_casa(client)

    resposta = client.post(
        UPLOADS,
        data={"casa_id": casa_id, "periodo": PERIODO},
        files={"arquivo": _csv()},
    )

    assert resposta.status_code == 201
    corpo = resposta.json()
    assert corpo["nome_original"] == "export.csv"
    assert corpo["tamanho_bytes"] > 0
    assert corpo["itens_importados"] == 2


def test_blob_name_nao_reusa_o_nome_enviado(client):
    casa_id = _criar_casa(client)

    corpo = client.post(
        UPLOADS, data={"casa_id": casa_id, "periodo": PERIODO}, files={"arquivo": _csv()}
    ).json()

    assert corpo["blob_name"] != "export.csv"
    assert corpo["blob_name"].endswith(".csv")
    assert "/" not in corpo["blob_name"] and ".." not in corpo["blob_name"]


def test_upload_para_casa_inexistente_devolve_404(client):
    resposta = client.post(
        UPLOADS, data={"casa_id": 999, "periodo": PERIODO}, files={"arquivo": _csv()}
    )
    assert resposta.status_code == 404


def test_tipo_nao_permitido_devolve_415(client):
    casa_id = _criar_casa(client)
    arquivo = ("script.exe", io.BytesIO(b"MZ..."), "application/x-msdownload")

    resposta = client.post(
        UPLOADS, data={"casa_id": casa_id, "periodo": PERIODO}, files={"arquivo": arquivo}
    )
    assert resposta.status_code == 415


def test_arquivo_vazio_devolve_422(client):
    casa_id = _criar_casa(client)
    arquivo = ("vazio.csv", io.BytesIO(b""), "text/csv")

    resposta = client.post(
        UPLOADS, data={"casa_id": casa_id, "periodo": PERIODO}, files={"arquivo": arquivo}
    )
    assert resposta.status_code == 422


def test_coluna_obrigatoria_faltando_devolve_422(client):
    casa_id = _criar_casa(client)
    arquivo = _csv("item,custo_real\nGrey Goose,120\n")

    resposta = client.post(
        UPLOADS, data={"casa_id": casa_id, "periodo": PERIODO}, files={"arquivo": arquivo}
    )
    assert resposta.status_code == 422
    assert "custo_teorico" in resposta.json()["detail"]


def test_arquivo_grande_demais_devolve_413(client):
    from app.config import settings

    casa_id = _criar_casa(client)
    excesso = b"x" * (settings.max_upload_mb * 1024 * 1024 + 1)
    arquivo = ("grande.csv", io.BytesIO(excesso), "text/csv")

    resposta = client.post(
        UPLOADS, data={"casa_id": casa_id, "periodo": PERIODO}, files={"arquivo": arquivo}
    )
    assert resposta.status_code == 413


def test_periodo_mal_formatado_devolve_422(client):
    casa_id = _criar_casa(client)
    resposta = client.post(
        UPLOADS, data={"casa_id": casa_id, "periodo": "09/2026"}, files={"arquivo": _csv()}
    )
    assert resposta.status_code == 422


def test_listar_uploads_paginado(client):
    casa_id = _criar_casa(client)
    client.post(UPLOADS, data={"casa_id": casa_id, "periodo": PERIODO}, files={"arquivo": _csv()})

    resposta = client.get(UPLOADS)

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["total"] == 1
    assert len(corpo["items"]) == 1


# -------------------------------------------------------------- Delta (RF02)
def test_delta_calcula_totais_e_ordena_por_maior_delta(client):
    casa_id = _criar_casa(client)
    client.post(UPLOADS, data={"casa_id": casa_id, "periodo": PERIODO}, files={"arquivo": _csv()})

    resposta = client.get(DELTA, params={"casa_id": casa_id, "periodo": PERIODO})

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["custo_teorico_total"] == 150.0
    assert corpo["custo_real_total"] == 165.0
    assert corpo["delta_total"] == 15.0
    # Grey Goose tem o maior delta em módulo (|120-100|=20 > |45-50|=5)
    assert corpo["itens"][0]["nome"] == "Grey Goose"


def test_delta_sem_dado_no_periodo_devolve_404(client):
    casa_id = _criar_casa(client)
    client.post(UPLOADS, data={"casa_id": casa_id, "periodo": PERIODO}, files={"arquivo": _csv()})

    resposta = client.get(DELTA, params={"casa_id": casa_id, "periodo": "2026-01"})

    assert resposta.status_code == 404
    assert "2026-01" in resposta.json()["detail"]


def test_delta_casa_inexistente_devolve_404(client):
    resposta = client.get(DELTA, params={"casa_id": 999, "periodo": PERIODO})
    assert resposta.status_code == 404
