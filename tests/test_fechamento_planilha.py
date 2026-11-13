"""Fechamento pela planilha-modelo (12/11/2026).

Uma linha por grupo por mês com venda, custo teórico e movimento de estoque:
o lado real é o CMV real (EI + compras − EF), sem depender da DRE. Os números
de referência são os do exemplo da própria planilha-modelo, conferidos à mão:

    mês      grupo      EI usado   CMV real   real %   teórico %   ajuste
    2026-07  ALIMENTOS    40.000     68.000    27,20     27,00     +500
    2026-07  BEBIDAS     100.000     77.000    25,67     25,00   +2.000
    2026-08  ALIMENTOS    42.000     76.000    28,15     27,00   +3.100
    2026-08  BEBIDAS      95.000     81.000    25,31     25,00   +1.000
    2026-09  ALIMENTOS    44.000     65.000    27,08     27,00     +200
    2026-09  BEBIDAS     104.000     75.000    25,86     25,00   +2.500
"""

import io
from datetime import datetime

import pytest
from openpyxl import load_workbook

from app import crud
from app.services.leitor_fechamento import ler_fechamento
from app.services.leitores import ErroLeitura
from tests.planilhas import cardapio_xlsx, dre_xlsx, xlsx
from tests.test_dialeto_sql import _colunas_soltas_no_group_by

CASAS = "/api/v1/casas"
FECHAMENTOS = "/api/v1/fechamentos"
MODELO = "/api/v1/modelos/fechamento"
FECHAMENTO = "/api/v1/metricas/fechamento"
EVOLUCAO = "/api/v1/metricas/evolucao"
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

CABECALHO = [
    "periodo", "grupo", "venda_liquida", "custo_teorico",
    "estoque_inicial", "compras", "estoque_final",
]  # fmt: skip


def planilha(*linhas, cabecalho=CABECALHO) -> bytes:
    return xlsx({"Fechamento": [cabecalho, *linhas]})


def _linha(periodo, grupo, venda=1000, teorico=300, ei=None, compras=300, ef=100):
    return [periodo, grupo, venda, teorico, ei, compras, ef]


@pytest.fixture
def casa_id(client) -> int:
    casa = {"nome": "Casa Planilha", "marca": "Teste", "cidade": "São Paulo"}
    return client.post(CASAS, json=casa).json()["id"]


def _enviar(client, casa_id, conteudo, nome="fechamento.xlsx"):
    return client.post(
        FECHAMENTOS,
        data={"casa_id": casa_id},
        files={"arquivo": (nome, io.BytesIO(conteudo), XLSX)},
    )


def _fechamento(client, casa_id, periodo) -> dict:
    resposta = client.get(FECHAMENTO, params={"casa_id": casa_id, "periodo": periodo})
    assert resposta.status_code == 200, resposta.text
    return resposta.json()


def _grupos(fechamento: dict) -> dict:
    return {g["grupo"]: g for g in fechamento["grupos"]}


# ---------------------------------------------------------------- modelo
def test_modelo_e_um_xlsx_com_as_tres_abas(client):
    resposta = client.get(MODELO)

    assert resposta.status_code == 200
    assert resposta.headers["content-type"] == XLSX
    assert "modelo-fechamento.xlsx" in resposta.headers["content-disposition"]
    livro = load_workbook(io.BytesIO(resposta.content))
    assert livro.sheetnames == ["Fechamento", "Instrucoes", "Conferencia"]
    cabecalho = [c.value for c in livro["Fechamento"][1]]
    assert cabecalho == CABECALHO


def test_modelo_baixado_e_aceito_e_fecha_com_os_numeros_conferidos(client, casa_id):
    """O teste que importa: o arquivo que a API manda baixar é aceito de volta,
    e a conta bate com a feita à mão (docstring do módulo)."""
    resposta = _enviar(client, casa_id, client.get(MODELO).content)

    assert resposta.status_code == 201, resposta.text
    corpo = resposta.json()
    assert corpo["periodos"] == ["2026-07", "2026-08", "2026-09"]
    assert corpo["linhas_importadas"] == 6
    assert corpo["meses_substituidos"] == []

    setembro = _fechamento(client, casa_id, "2026-09")
    assert setembro["base_real"] == "consumo"
    assert setembro["tem_cardapio"] and setembro["tem_compras"]
    grupos = _grupos(setembro)
    # EI de setembro em branco na planilha → EF de agosto (44.000 e 104.000)
    assert grupos["ALIMENTOS"]["custo_real"] == 65000
    assert grupos["ALIMENTOS"]["cmv_real_pct"] == 27.08
    assert grupos["ALIMENTOS"]["ajuste"] == 200
    assert grupos["BEBIDAS"]["custo_real"] == 75000
    assert grupos["BEBIDAS"]["ajuste_pp"] == 0.86
    assert setembro["total"]["custo_real"] == 140000
    assert setembro["total"]["ajuste"] == 2700

    agosto = _grupos(_fechamento(client, casa_id, "2026-08"))
    assert agosto["ALIMENTOS"]["custo_real"] == 76000
    assert agosto["BEBIDAS"]["custo_real"] == 81000


def test_com_estoque_o_mes_e_conclusivo(client, casa_id):
    _enviar(client, casa_id, client.get(MODELO).content)

    setembro = _fechamento(client, casa_id, "2026-09")

    assert setembro["explicacao"]["conclusivo"] is True
    assert setembro["explicacao"]["subgrupos_comparados"] == []
    assert setembro["acumulado"]["meses"] == 3
    assert setembro["acumulado"]["base_real"] == "consumo"
    assert setembro["acumulado"]["conclusivo"] is True
    # 68+77+76+81+65+75 mil de real contra 67,5+75+72,9+80+64,8+72,5 mil de teórico
    assert setembro["acumulado"]["total"]["ajuste"] == 9300


def test_evolucao_usa_os_meses_da_planilha(client, casa_id):
    _enviar(client, casa_id, client.get(MODELO).content)

    pontos = client.get(EVOLUCAO, params={"casa_id": casa_id}).json()

    assert [p["periodo"] for p in pontos] == ["2026-07", "2026-08", "2026-09"]
    assert {p["base_real"] for p in pontos} == {"consumo"}


# ---------------------------------------------------------------- leitor
def test_leitor_aceita_periodo_como_data_ou_mm_aaaa_e_numero_como_texto():
    """O Excel converte '2026-09' digitado sem formato de texto em data; o
    usuário não errou. Texto com vírgula ou ponto decimal também vale."""
    movimentos = ler_fechamento(
        planilha(
            [datetime(2026, 9, 1), " alimentos ", "1.234,56", 300, 50, "1234.5", 80],
            ["09/2026", "Bebidas", 2000, None, 10, 400, 20],
        )
    )

    alimentos, bebidas = movimentos
    assert (alimentos.periodo, alimentos.grupo) == ("2026-09", "ALIMENTOS")
    assert alimentos.venda_liquida == 1234.56
    assert alimentos.compras == 1234.5
    assert (bebidas.periodo, bebidas.grupo, bebidas.custo_teorico) == ("2026-09", "BEBIDAS", None)


def test_leitor_aceita_colunas_em_outra_ordem_e_sem_as_opcionais():
    conteudo = planilha(
        ["2026-09", 500, 100, 1000, "ALIMENTOS"],
        cabecalho=["Período", "Compras", "Estoque Final", "Venda Líquida", "Grupo"],
    )

    (movimento,) = ler_fechamento(conteudo)

    assert movimento.estoque_inicial is None and movimento.custo_teorico is None
    assert (movimento.compras, movimento.estoque_final) == (500, 100)


def test_leitor_lista_todos_os_erros_com_o_numero_da_linha():
    conteudo = planilha(
        _linha("2026-09", "ALIMENTOS", ei=10),
        _linha("2026-13", "BEBIDAS", ei=10),
        _linha("2026-09", "CARNES", ei=10, ef=None),
        _linha("2026-09", "PEIXES", ei=10, compras=-5),
        _linha("2026-09", "alimentos", ei=10),
        ["2026-09", "QUEIJOS", "abc", 1, 10, 1, 1],
    )

    with pytest.raises(ErroLeitura) as erro:
        ler_fechamento(conteudo)

    mensagem = str(erro.value)
    assert "Linha 3: período '2026-13' inválido" in mensagem
    assert "Linha 4: falta o estoque_final" in mensagem
    assert "Linha 5: compras negativo" in mensagem
    assert "Linha 6: ALIMENTOS em 2026-09 repetido (já na linha 2)" in mensagem
    assert "Linha 7: venda_liquida 'abc' não é um número" in mensagem


def test_leitor_ignora_linhas_em_branco():
    conteudo = planilha(_linha("2026-09", "ALIMENTOS", ei=10), [], [None, None, None])

    assert len(ler_fechamento(conteudo)) == 1


@pytest.mark.parametrize(
    "conteudo",
    [
        xlsx({"Plan1": [["grupo", "custo"], ["ALIMENTOS", 10]]}),
        planilha(),
    ],
    ids=["sem as colunas", "sem linhas"],
)
def test_leitor_recusa_arquivo_que_nao_e_a_planilha(conteudo):
    with pytest.raises(ErroLeitura):
        ler_fechamento(conteudo)


# ---------------------------------------------------------------- envio
def test_primeiro_mes_sem_estoque_inicial_e_recusado(client, casa_id):
    resposta = _enviar(client, casa_id, planilha(_linha("2026-09", "ALIMENTOS")))

    assert resposta.status_code == 422
    assert "ALIMENTOS em 2026-09" in resposta.json()["detail"]
    assert client.get(FECHAMENTOS, params={"casa_id": casa_id}).json()["total"] == 0


def test_estoque_inicial_em_branco_usa_o_final_de_um_envio_anterior(client, casa_id):
    _enviar(client, casa_id, planilha(_linha("2026-08", "ALIMENTOS", ei=100, ef=70)))

    resposta = _enviar(client, casa_id, planilha(_linha("2026-09", "ALIMENTOS", ef=50)))

    assert resposta.status_code == 201, resposta.text
    # 70 (EF de agosto) + 300 − 50
    assert _grupos(_fechamento(client, casa_id, "2026-09"))["ALIMENTOS"]["custo_real"] == 320


def test_mes_anterior_no_arquivo_substitui_o_do_banco_na_conferencia(client, casa_id):
    """Agosto no arquivo troca agosto inteiro: o EF de ALIMENTOS gravado antes
    deixa de existir, então não pode servir de abertura para setembro."""
    _enviar(client, casa_id, planilha(_linha("2026-08", "ALIMENTOS", ei=100)))

    resposta = _enviar(
        client,
        casa_id,
        planilha(_linha("2026-08", "BEBIDAS", ei=10), _linha("2026-09", "ALIMENTOS")),
    )

    assert resposta.status_code == 422
    assert "ALIMENTOS em 2026-09" in resposta.json()["detail"]


def test_reenvio_troca_o_mes_inteiro_e_mantem_os_outros(client, casa_id):
    _enviar(client, casa_id, client.get(MODELO).content)

    resposta = _enviar(
        client, casa_id, planilha(_linha("2026-09", "ALIMENTOS", teorico=None, ef=44000))
    )

    assert resposta.status_code == 201, resposta.text
    assert resposta.json()["meses_substituidos"] == ["2026-09"]
    setembro = _fechamento(client, casa_id, "2026-09")
    assert [g["grupo"] for g in setembro["grupos"]] == ["ALIMENTOS"]  # BEBIDAS saiu
    assert len(_fechamento(client, casa_id, "2026-08")["grupos"]) == 2

    envios = client.get(FECHAMENTOS, params={"casa_id": casa_id}).json()["items"]
    assert [e["periodos"] for e in envios] == [["2026-09"], ["2026-07", "2026-08"]]


def test_envio_que_fica_sem_nenhum_mes_e_apagado(client, casa_id):
    modelo = client.get(MODELO).content
    _enviar(client, casa_id, modelo)

    _enviar(client, casa_id, modelo)

    envios = client.get(FECHAMENTOS, params={"casa_id": casa_id}).json()
    assert envios["total"] == 1
    assert envios["items"][0]["linhas_importadas"] == 6


def test_sem_custo_teorico_mostra_o_real_sem_ajuste(client, casa_id):
    _enviar(client, casa_id, planilha(_linha("2026-09", "ALIMENTOS", teorico=None, ei=100)))

    setembro = _fechamento(client, casa_id, "2026-09")

    assert setembro["tem_cardapio"] is False
    assert setembro["total"]["custo_real"] == 300
    assert setembro["total"]["cmv_real_pct"] == 30.0
    assert setembro["total"]["ajuste"] is None
    assert setembro["explicacao"] is None


def test_total_nao_soma_teorico_de_um_grupo_contra_real_de_dois(client, casa_id):
    _enviar(
        client,
        casa_id,
        planilha(
            _linha("2026-09", "ALIMENTOS", ei=100),
            _linha("2026-09", "BEBIDAS", teorico=None, ei=100),
        ),
    )

    total = _fechamento(client, casa_id, "2026-09")["total"]

    assert total["custo_teorico"] is None
    assert total["ajuste"] is None
    assert total["custo_real"] == 600


def test_casa_com_planilha_deixa_de_usar_os_relatorios_do_everest(client, casa_id):
    for tipo, conteudo in (("cardapio", cardapio_xlsx()), ("compras", dre_xlsx())):
        client.post(
            "/api/v1/uploads-custo",
            data={"casa_id": casa_id, "periodo": "2026-09", "tipo": tipo},
            files={"arquivo": ("x.xlsx", io.BytesIO(conteudo), XLSX)},
        )
    assert _fechamento(client, casa_id, "2026-09")["base_real"] == "compras"

    _enviar(client, casa_id, planilha(_linha("2026-09", "ALIMENTOS", ei=100)))

    setembro = _fechamento(client, casa_id, "2026-09")
    assert setembro["base_real"] == "consumo"
    assert [g["grupo"] for g in setembro["grupos"]] == ["ALIMENTOS"]


def test_casa_inexistente_devolve_404(client):
    assert _enviar(client, 999, planilha(_linha("2026-09", "A", ei=1))).status_code == 404


def test_arquivo_que_nao_e_xlsx_devolve_415(client, casa_id):
    resposta = client.post(
        FECHAMENTOS,
        data={"casa_id": casa_id},
        files={"arquivo": ("dados.csv", io.BytesIO(b"a,b"), "text/csv")},
    )
    assert resposta.status_code == 415


def test_remover_casa_apaga_os_envios(client, casa_id):
    _enviar(client, casa_id, client.get(MODELO).content)

    assert client.delete(f"{CASAS}/{casa_id}").status_code == 204
    assert client.get(FECHAMENTOS, params={"casa_id": casa_id}).json()["total"] == 0


def test_listagem_por_envio_e_compativel_com_sql_server():
    stmt = crud.stmt_periodos_por_upload_fechamento([1, 2])

    assert _colunas_soltas_no_group_by(stmt) == []
