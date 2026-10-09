"""CRUD de itens.

Cada teste amarra um comportamento que a Aula 04 cobrou explicitamente:
201 ao criar, 404 ao não achar, 422 quando o dado é inválido, 204 ao apagar.
"""

import pytest

BASE = "/api/v1/itens"


# ------------------------------------------------------------------ POST
def test_criar_devolve_201_e_id(client, item_valido):
    resposta = client.post(BASE, json=item_valido)

    assert resposta.status_code == 201, "Criar recurso é 201 Created, não 200 OK"
    corpo = resposta.json()
    assert corpo["id"] > 0
    assert corpo["nome"] == item_valido["nome"]
    assert "criado_em" in corpo


def test_post_nao_e_idempotente(client, item_valido):
    """Mandar o mesmo POST duas vezes cria dois recursos.

    É exatamente o que acontece quando o usuário clica duas vezes no botão.
    """
    a = client.post(BASE, json=item_valido).json()
    b = client.post(BASE, json=item_valido).json()

    assert a["id"] != b["id"]
    assert client.get(BASE).json()["total"] == 2


@pytest.mark.parametrize(
    ("campo", "valor", "motivo"),
    [
        ("nome", "AB", "nome tem min_length=3"),
        ("nome", "x" * 200, "nome tem max_length=120"),
        ("quantidade", -1, "quantidade tem ge=0"),
        ("valor", -5, "valor tem ge=0"),
        ("categoria", "a", "categoria tem min_length=2"),
    ],
)
def test_validacao_devolve_422(client, item_valido, campo, valor, motivo):
    """Nenhum `if` foi escrito para isto — o Pydantic valida pelo tipo declarado."""
    payload = {**item_valido, campo: valor}
    assert client.post(BASE, json=payload).status_code == 422, motivo


def test_campo_obrigatorio_ausente_devolve_422(client, item_valido):
    payload = {k: v for k, v in item_valido.items() if k != "categoria"}
    resposta = client.post(BASE, json=payload)

    assert resposta.status_code == 422
    assert "categoria" in str(resposta.json())


# ------------------------------------------------------------------- GET
def test_get_e_idempotente(client, item_valido):
    """Chamar GET N vezes devolve o mesmo e não altera nada no servidor."""
    client.post(BASE, json=item_valido)
    respostas = [client.get(BASE).json() for _ in range(3)]

    assert respostas[0] == respostas[1] == respostas[2]
    assert respostas[0]["total"] == 1


def test_buscar_existente_devolve_200(client, item_valido):
    item_id = client.post(BASE, json=item_valido).json()["id"]
    resposta = client.get(f"{BASE}/{item_id}")

    assert resposta.status_code == 200
    assert resposta.json()["id"] == item_id


def test_buscar_inexistente_devolve_404(client):
    """404, não 200 com null: devolver null obriga o front a adivinhar."""
    resposta = client.get(f"{BASE}/999")

    assert resposta.status_code == 404
    assert "999" in resposta.json()["detail"]


def test_id_nao_numerico_devolve_422(client):
    """`item_id: int` na assinatura já barra 'abc' antes de entrar na função."""
    assert client.get(f"{BASE}/abc").status_code == 422


def test_paginacao_e_filtros(client, item_valido):
    for i in range(5):
        client.post(
            BASE,
            json={**item_valido, "nome": f"Item {i}", "categoria": "cat-a" if i < 3 else "cat-b"},
        )

    pagina = client.get(BASE, params={"limit": 2, "offset": 0}).json()
    assert pagina["total"] == 5
    assert len(pagina["items"]) == 2

    filtrado = client.get(BASE, params={"categoria": "cat-a"}).json()
    assert filtrado["total"] == 3

    busca = client.get(BASE, params={"busca": "Item 4"}).json()
    assert busca["total"] == 1


# ----------------------------------------------------------------- PATCH
def test_patch_altera_somente_o_que_foi_enviado(client, item_valido):
    item_id = client.post(BASE, json=item_valido).json()["id"]

    resposta = client.patch(f"{BASE}/{item_id}", json={"quantidade": 99})

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["quantidade"] == 99
    assert corpo["nome"] == item_valido["nome"], "campo omitido não pode ser apagado"


def test_patch_em_inexistente_devolve_404(client):
    assert client.patch(f"{BASE}/999", json={"quantidade": 1}).status_code == 404


# ---------------------------------------------------------------- DELETE
def test_delete_devolve_204_sem_corpo(client, item_valido):
    item_id = client.post(BASE, json=item_valido).json()["id"]
    resposta = client.delete(f"{BASE}/{item_id}")

    assert resposta.status_code == 204
    assert resposta.content == b""
    assert client.get(f"{BASE}/{item_id}").status_code == 404


def test_delete_repetido_devolve_404(client, item_valido):
    """DELETE é idempotente no efeito: o recurso segue ausente.

    A segunda chamada devolve 404 porque o recurso já não existe — o estado
    final é o mesmo, que é o que idempotência garante.
    """
    item_id = client.post(BASE, json=item_valido).json()["id"]

    assert client.delete(f"{BASE}/{item_id}").status_code == 204
    assert client.delete(f"{BASE}/{item_id}").status_code == 404
