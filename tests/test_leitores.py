"""Tradutores dos exports do Everest (app/services/leitores.py)."""

import pytest

from app.services.leitores import ErroLeitura, ler_cardapio, ler_compras, nome_aba_do_periodo
from tests.planilhas import cardapio_xlsx, dre_xlsx, linhas_cardapio, xlsx

PERIODO = "2026-09"


def test_cardapio_extrai_grupos_subgrupos_e_itens():
    extracao = ler_cardapio(cardapio_xlsx(), PERIODO)

    grupos = {g.nome: g for g in extracao.por_nivel("grupo")}
    assert set(grupos) == {"ALIMENTOS", "BEBIDAS", "SERVICOS"}
    assert grupos["ALIMENTOS"].custo == 300
    assert grupos["ALIMENTOS"].venda_liquida == 1000

    itens = {i.nome: i for i in extracao.por_nivel("item")}
    assert itens["BOLINHO"].grupo == "ALIMENTOS"
    assert itens["BOLINHO"].subgrupo == "PETISCOS"
    assert itens["CHOPP 300ML"].subgrupo == "CHOPP"


def test_cardapio_usa_o_primeiro_resultado_final_e_ignora_eventos():
    total = ler_cardapio(cardapio_xlsx(), PERIODO).por_nivel("total")

    assert len(total) == 1
    assert total[0].custo == 700  # não 9999, que é o bloco com eventos lançado à mão
    assert total[0].venda_liquida == 3100


def test_cardapio_com_varias_abas_escolhe_a_do_periodo():
    arquivo = xlsx(
        {
            "AGOSTO26 24,96": linhas_cardapio(fator=2),
            "SETEMBRO26 25,17": linhas_cardapio(fator=1),
        }
    )

    agosto = ler_cardapio(arquivo, "2026-08").por_nivel("total")[0]
    setembro = ler_cardapio(arquivo, "2026-09").por_nivel("total")[0]

    assert agosto.custo == 1400
    assert setembro.custo == 700


def test_cardapio_sem_aba_do_periodo_da_erro_claro():
    arquivo = xlsx({"AGOSTO26": linhas_cardapio(), "SETEMBRO26": linhas_cardapio()})

    with pytest.raises(ErroLeitura, match="OUTUBRO26"):
        ler_cardapio(arquivo, "2026-10")


def test_arquivo_que_nao_e_cardapio_da_erro_claro():
    with pytest.raises(ErroLeitura, match="engenharia de cardápio"):
        ler_cardapio(dre_xlsx(), PERIODO)


def test_compras_extrai_receita_grupos_e_subgrupos():
    extracao = ler_compras(dre_xlsx(), PERIODO)

    total = extracao.por_nivel("total")[0]
    assert total.venda_liquida == 3200
    assert total.custo == 1000

    grupos = {g.nome: g.custo for g in extracao.por_nivel("grupo")}
    assert grupos == {"ALIMENTOS": 330, "BEBIDAS": 420, "MATERIAL DE CONSUMO": 250}

    subgrupos = {s.nome: s.grupo for s in extracao.por_nivel("subgrupo")}
    assert subgrupos["BOVINOS"] == "ALIMENTOS"
    assert subgrupos["CHOPP"] == "BEBIDAS"


def test_arquivo_que_nao_e_dre_da_erro_claro():
    with pytest.raises(ErroLeitura, match="DRE"):
        ler_compras(cardapio_xlsx(), PERIODO)


def test_bytes_que_nao_sao_xlsx_dao_erro_claro():
    with pytest.raises(ErroLeitura, match=".xlsx"):
        ler_cardapio(b"isto nao e uma planilha", PERIODO)


@pytest.mark.parametrize(
    ("periodo", "aba"),
    [("2026-09", "SETEMBRO26"), ("2026-03", "MARCO26"), ("2025-01", "JANEIRO25")],
)
def test_nome_aba_do_periodo(periodo, aba):
    assert nome_aba_do_periodo(periodo) == aba
