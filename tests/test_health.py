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


def test_health_expoe_o_commit_publicado(client):
    """O workflow de deploy compara este campo com o SHA que acabou de publicar.

    Sem ele, a verificação pós-deploy só provava que a aplicação respondia — e
    em 06/11/2026 ela respondia com o código ANTIGO, enquanto o workflow dava
    sucesso. Fora do deploy automatizado o valor é 'desconhecido', nunca ausente:
    campo que às vezes não existe quebra quem consome.
    """
    corpo = client.get("/health").json()

    assert "commit" in corpo
    assert corpo["commit"] == "desconhecido"


def test_openapi_disponivel(client):
    """O contrato da API precisa existir — é dele que o /docs é gerado."""
    resposta = client.get("/openapi.json")
    assert resposta.status_code == 200
    assert "/api/v1/casas" in resposta.json()["paths"]
