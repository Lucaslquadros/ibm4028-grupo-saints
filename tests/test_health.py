"""O /health é o que o Azure App Service usa para decidir se reinicia a instância.

Se este teste quebrar, o deploy pode subir e o Azure derrubar em seguida.
"""


def test_raiz_responde(client):
    resposta = client.get("/")
    assert resposta.status_code == 200
    assert resposta.json()["docs"] == "/docs"


def test_health_ok(client):
    resposta = client.get("/health")
    assert resposta.status_code == 200

    corpo = resposta.json()
    assert corpo["status"] == "ok"
    assert corpo["banco"] == "ok"


def test_openapi_disponivel(client):
    """O contrato da API precisa existir — é dele que o /docs é gerado."""
    resposta = client.get("/openapi.json")
    assert resposta.status_code == 200
    assert "/api/v1/itens" in resposta.json()["paths"]
