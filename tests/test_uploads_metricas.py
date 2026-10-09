"""Upload de arquivos e métricas do dashboard.

Os testes de upload rodam no modo local do storage (sem connection string do
Azure), então não dependem de credencial nem de rede.
"""

import io

ARQUIVOS = "/api/v1/arquivos"
ITENS = "/api/v1/itens"
METRICAS = "/api/v1/metricas/resumo"


def _csv(conteudo: str = "nome,quantidade\nRacao,10\n") -> tuple:
    return ("vendas.csv", io.BytesIO(conteudo.encode()), "text/csv")


# ---------------------------------------------------------------- Upload
def test_upload_csv_devolve_201(client):
    resposta = client.post(ARQUIVOS, files={"arquivo": _csv()})

    assert resposta.status_code == 201
    corpo = resposta.json()
    assert corpo["nome_original"] == "vendas.csv"
    assert corpo["tamanho_bytes"] > 0


def test_blob_name_nao_reusa_o_nome_enviado(client):
    """Nome vindo do cliente não pode virar caminho no storage.

    Reaproveitar permitiria sobrescrever arquivo alheio e path traversal.
    """
    corpo = client.post(ARQUIVOS, files={"arquivo": _csv()}).json()

    assert corpo["blob_name"] != "vendas.csv"
    assert corpo["blob_name"].endswith(".csv")
    assert "/" not in corpo["blob_name"] and ".." not in corpo["blob_name"]


def test_tipo_nao_permitido_devolve_415(client):
    arquivo = ("script.exe", io.BytesIO(b"MZ..."), "application/x-msdownload")
    assert client.post(ARQUIVOS, files={"arquivo": arquivo}).status_code == 415


def test_arquivo_vazio_devolve_422(client):
    arquivo = ("vazio.csv", io.BytesIO(b""), "text/csv")
    assert client.post(ARQUIVOS, files={"arquivo": arquivo}).status_code == 422


def test_arquivo_grande_demais_devolve_413(client):
    from app.config import settings

    excesso = b"x" * (settings.max_upload_mb * 1024 * 1024 + 1)
    arquivo = ("grande.csv", io.BytesIO(excesso), "text/csv")

    assert client.post(ARQUIVOS, files={"arquivo": arquivo}).status_code == 413


def test_listar_arquivos(client):
    client.post(ARQUIVOS, files={"arquivo": _csv()})
    resposta = client.get(ARQUIVOS)

    assert resposta.status_code == 200
    assert len(resposta.json()) == 1


# -------------------------------------------------------------- Métricas
def test_resumo_vazio(client):
    corpo = client.get(METRICAS).json()

    assert corpo["total_itens"] == 0
    assert corpo["valor_total_estoque"] == 0
    assert corpo["por_categoria"] == []


def test_resumo_agrega_por_categoria(client, item_valido):
    client.post(ITENS, json={**item_valido, "categoria": "cat-a", "quantidade": 2, "valor": 10})
    client.post(ITENS, json={**item_valido, "categoria": "cat-a", "quantidade": 3, "valor": 10})
    client.post(ITENS, json={**item_valido, "categoria": "cat-b", "quantidade": 1, "valor": 100})

    corpo = client.get(METRICAS).json()

    assert corpo["total_itens"] == 3
    assert corpo["quantidade_total"] == 6
    assert corpo["valor_total_estoque"] == 150.0  # (2*10) + (3*10) + (1*100)

    por_cat = {c["categoria"]: c for c in corpo["por_categoria"]}
    assert por_cat["cat-a"]["quantidade_itens"] == 2
    assert por_cat["cat-a"]["valor_total"] == 50.0
    assert por_cat["cat-b"]["valor_total"] == 100.0
