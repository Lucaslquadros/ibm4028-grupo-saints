"""O fechamento funciona fora do Everest e fora de um restaurante.

Estes testes existem para sustentar uma afirmação específica do projeto: a de
que o sistema resolve a dor do fechamento manual para **outro negócio**, e não
só para o Grupo Saints. Sem eles a afirmação seria slide, não software.

Duas coisas precisavam ser verdade, e cada uma tem um teste aqui:

1. **Origem do dado.** `app/services/leitores.py` tinha dois tradutores, ambos
   de relatórios do Everest. O terceiro (`ler_planilha`) lê uma tabela comum,
   que qualquer ERP exporta, e produz a mesma `LinhaCusto`.

2. **Domínio do cálculo.** `crud.py` tinha `GRUPOS_CMV = ("ALIMENTOS",
   "BEBIDAS")` cravado. Categoria de restaurante no código invalida qualquer
   generalização — uma farmácia não vende "bebidas". Agora os grupos são
   deduzidos: comparável é o grupo que os **dois** lados reportam.

O domínio dos testes é uma farmácia, de propósito. Números em tests/planilhas.py.
"""

import io

import pytest

from tests.planilhas import planilha_real_xlsx, planilha_teorico_xlsx

CASAS = "/api/v1/casas"
UPLOADS = "/api/v1/uploads-custo"
FECHAMENTO = "/api/v1/metricas/fechamento"
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
PERIODO = "2026-09"


@pytest.fixture
def farmacia_id(client) -> int:
    unidade = {"nome": "Drogaria Central - Centro", "marca": "Drogaria Central",
               "cidade": "São Paulo"}  # fmt: skip
    return client.post(CASAS, json=unidade).json()["id"]


def _enviar(client, casa_id, tipo, conteudo, periodo=PERIODO):
    resposta = client.post(
        UPLOADS,
        data={"casa_id": casa_id, "periodo": periodo, "tipo": tipo},
        files={"arquivo": ("qualquer-erp.xlsx", io.BytesIO(conteudo), XLSX)},
    )
    assert resposta.status_code == 201, resposta.text
    return resposta.json()


def test_planilha_generica_e_aceita_sem_declarar_o_formato(client, farmacia_id):
    """O usuário diz o LADO do fechamento (teórico/real), nunca o formato.

    O mesmo `tipo=cardapio` que recebe a engenharia de cardápio do Everest
    aceita esta planilha: o despacho em `leitores.ler` tenta o leitor
    específico, não reconhece, e cai no genérico.
    """
    corpo = _enviar(client, farmacia_id, "cardapio", planilha_teorico_xlsx())

    # 1 total + 2 grupos + 2 subgrupos + 3 itens
    assert corpo["linhas_importadas"] == 8


def test_fechamento_completo_num_negocio_que_nao_e_restaurante(client, farmacia_id):
    _enviar(client, farmacia_id, "cardapio", planilha_teorico_xlsx())
    _enviar(client, farmacia_id, "compras", planilha_real_xlsx())

    corpo = client.get(FECHAMENTO, params={"casa_id": farmacia_id, "periodo": PERIODO}).json()

    grupos = {g["grupo"]: g for g in corpo["grupos"]}
    assert grupos["MEDICAMENTOS"]["cmv_teorico_pct"] == 43.33
    assert grupos["MEDICAMENTOS"]["cmv_real_pct"] == 46.67
    assert grupos["MEDICAMENTOS"]["ajuste"] == 50.0
    assert grupos["PERFUMARIA"]["cmv_teorico_pct"] == 50.0
    assert grupos["PERFUMARIA"]["cmv_real_pct"] == 53.33

    total = corpo["total"]
    assert total["venda_liquida"] == 2100.0
    assert total["custo_teorico"] == 950.0
    assert total["custo_real"] == 1020.0
    assert total["cmv_teorico_pct"] == 45.24
    assert total["cmv_real_pct"] == 48.57
    assert total["ajuste"] == 70.0
    assert total["ajuste_pp"] == 3.33


def test_grupo_presente_em_um_lado_so_fica_fora_do_cmv(client, farmacia_id):
    """EMBALAGENS aparece só no lado real — é o equivalente a UTENSILIOS na DRE
    do restaurante. Sem ser reportado pelos dois lados não há teórico para
    comparar, então não entra no CMV direto nem no total."""
    _enviar(client, farmacia_id, "cardapio", planilha_teorico_xlsx())
    _enviar(client, farmacia_id, "compras", planilha_real_xlsx())

    corpo = client.get(FECHAMENTO, params={"casa_id": farmacia_id, "periodo": PERIODO}).json()

    assert {g["grupo"] for g in corpo["grupos"]} == {"MEDICAMENTOS", "PERFUMARIA"}
    # 1020 = 700 + 320, sem os 150 de EMBALAGENS
    assert corpo["total"]["custo_real"] == 1020.0


def test_colunas_fora_de_ordem_e_desconhecidas_nao_atrapalham(client, farmacia_id):
    """A planilha de teste tem as colunas em ordem trocada e uma coluna
    'Observação' que o leitor não conhece. Localizar coluna por nome e não por
    posição é o que permite aceitar o export de um ERP qualquer."""
    _enviar(client, farmacia_id, "cardapio", planilha_teorico_xlsx())

    corpo = client.get(FECHAMENTO, params={"casa_id": farmacia_id, "periodo": PERIODO}).json()

    assert corpo["total"]["venda_liquida"] == 2100.0
    assert corpo["total"]["custo_teorico"] == 950.0


def test_planilha_sem_as_colunas_minimas_devolve_422_citando_as_duas(client, farmacia_id):
    from tests.planilhas import xlsx

    sem_custo = xlsx({"Dados": [["Grupo", "Item"], ["MEDICAMENTOS", "DIPIRONA"]]})

    resposta = client.post(
        UPLOADS,
        data={"casa_id": farmacia_id, "periodo": PERIODO, "tipo": "cardapio"},
        files={"arquivo": ("ruim.xlsx", io.BytesIO(sem_custo), XLSX)},
    )

    assert resposta.status_code == 422
    detalhe = resposta.json()["detail"]
    assert "grupo" in detalhe and "custo" in detalhe
