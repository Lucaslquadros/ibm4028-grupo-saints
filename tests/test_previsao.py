"""Previsão de demanda por item — RF07.

A matemática é testada direto em `app/services/previsao.py`, sem banco e sem
HTTP, com números escolhidos para o resultado ser conferível na mão. É o único
jeito honesto de testar um cálculo que vai orientar decisão de compra: se o
teste precisa do resultado da função para saber o que esperar, não é teste.
"""

import pytest

from app.services.previsao import (
    LIMITE_SAZONAL_MAX,
    LIMITE_TENDENCIA,
    Ponto,
    alerta_volume,
    prever,
    proximo_periodo,
)


def _serie(valores: list[float], ano_inicio: int = 2025, mes_inicio: int = 1) -> list[Ponto]:
    pontos = []
    ano, mes = ano_inicio, mes_inicio
    for v in valores:
        pontos.append(Ponto(periodo=f"{ano}-{mes:02d}", quantidade=v))
        mes += 1
        if mes == 13:
            ano, mes = ano + 1, 1
    return pontos


def _prever(valores, periodo_alvo="2026-01", margem=0.0):
    return prever(
        nome="DIPIRONA",
        grupo="MEDICAMENTOS",
        subgrupo="GENERICOS",
        historico=_serie(valores),
        periodo_alvo=periodo_alvo,
        margem_seguranca_pct=margem,
    )


# ------------------------------------------------------------- próximo período
@pytest.mark.parametrize(
    ("periodo", "esperado"),
    [
        ("2026-09", "2026-10"),
        ("2026-11", "2026-12"),
        ("2026-12", "2027-01"),
        ("2026-01", "2026-02"),
    ],
)
def test_proximo_periodo_vira_o_ano_corretamente(periodo, esperado):
    assert proximo_periodo(periodo) == esperado


# ------------------------------------------------------------------ média móvel
def test_venda_estavel_preve_a_propria_media():
    # 12 meses de 100: sem tendência (100/100 - 1 = 0) e sem sazonalidade (índice 1,0)
    p = _prever([100] * 12)

    assert p.media_recente == 100.0
    assert p.tendencia_pct == 0.0
    assert p.demanda_prevista == 100.0


def test_media_usa_so_os_tres_ultimos_meses():
    # os 3 últimos são 60, 60, 60 → média 60, apesar dos 300 no começo
    p = _prever([300, 300, 300, 60, 60, 60])

    assert p.media_recente == 60.0


def test_margem_de_seguranca_entra_so_na_sugestao():
    p = _prever([100] * 12, margem=20.0)

    assert p.demanda_prevista == 100.0
    assert p.sugestao_compra == 120.0


# -------------------------------------------------------------------- tendência
def test_tendencia_de_alta_aumenta_a_previsao():
    # 3 primeiros: média 100. 3 últimos: média 120. Tendência = +20%
    p = _prever([100, 100, 100, 120, 120, 120])

    assert p.tendencia_pct == 20.0
    assert p.demanda_prevista == pytest.approx(144.0)  # 120 × 1,20


def test_tendencia_de_queda_reduz_a_previsao():
    p = _prever([100, 100, 100, 80, 80, 80])

    assert p.tendencia_pct == -20.0
    assert p.demanda_prevista == pytest.approx(64.0)  # 80 × 0,80


def test_sem_duas_janelas_completas_a_tendencia_e_nula_nao_zero():
    """`None` e `0.0` dizem coisas diferentes: "não sei" × "está estável".
    Devolver 0 aqui faria a tela afirmar estabilidade que ninguém verificou."""
    p = _prever([100, 100, 100, 100, 100])  # 5 meses, precisa de 6

    assert p.tendencia_pct is None
    assert p.demanda_prevista == 100.0


def test_explosao_de_venda_nao_vira_previsao_absurda():
    """Item que sai de 2 para 200 produziria tendência de +9900% sem trava."""
    p = _prever([2, 2, 2, 200, 200, 200])

    assert p.tendencia_pct == LIMITE_TENDENCIA * 100  # travado em +50%
    assert p.demanda_prevista == 300.0  # 200 × 1,5 — e não 200 × 100


# ------------------------------------------------------------------ sazonalidade
def _dezembro_forte() -> list[float]:
    """24 meses vendendo 100, exceto os dois dezembros, que vendem 200.

    Média geral = (22×100 + 2×200)/24 = 108,33
    Índice de dezembro = 200/108,33 = 1,846 | dos outros meses = 0,923
    """
    valores = [100.0] * 24
    valores[11] = 200.0  # 2025-12
    valores[23] = 200.0  # 2026-12
    return valores


def test_mes_historicamente_mais_forte_aumenta_a_previsao():
    # alvo 2026-12, previsto a partir do histórico até 2026-11
    p = prever(
        nome="X",
        grupo="G",
        subgrupo=None,
        historico=_serie(_dezembro_forte()[:23]),  # até 2026-11
        periodo_alvo="2026-12",
        margem_seguranca_pct=0,
    )

    assert p.indice_sazonal is not None
    assert p.indice_sazonal > 1.0  # dezembro vende acima da média
    assert p.demanda_prevista > 150.0  # e a previsão acompanha


def test_pico_sazonal_recente_nao_contamina_a_previsao_do_mes_seguinte():
    """Regressão do bug que o próprio teste pegou: prevendo janeiro logo depois
    de um dezembro forte, o pico entrava na média móvel e na tendência, e a
    previsão saía 164 em vez de 100. A série é dessazonalizada antes de medir
    patamar e tendência justamente para isso."""
    p = prever(
        nome="X",
        grupo="G",
        subgrupo=None,
        historico=_serie(_dezembro_forte()),  # termina em 2026-12, mês de pico
        periodo_alvo="2027-01",
        margem_seguranca_pct=0,
    )

    assert p.indice_sazonal == pytest.approx(0.923, abs=0.001)
    assert p.tendencia_pct == 0.0  # série plana depois de remover o efeito do mês
    assert p.demanda_prevista == pytest.approx(100.0, abs=0.5)


def test_sem_um_ano_de_historico_nao_ha_sazonalidade():
    p = _prever([100] * 11)  # 11 meses, precisa de 12

    assert p.indice_sazonal is None


def test_indice_sazonal_e_travado_no_maximo():
    # 12 meses de 1, exceto um mês de 1000 → índice bruto seria ~12
    valores = [1] * 12
    valores[0] = 1000  # 2025-01
    p = prever(
        nome="X",
        grupo="G",
        subgrupo=None,
        historico=_serie(valores),
        periodo_alvo="2026-01",
        margem_seguranca_pct=0,
    )

    assert p.indice_sazonal == LIMITE_SAZONAL_MAX


# --------------------------------------------------------------------- confiança
def test_historico_longo_e_estavel_da_confianca_alta():
    p = _prever([100] * 14)

    assert p.confianca == "alta"
    assert "14 meses" in p.motivo_confianca


def test_historico_longo_mas_oscilante_nao_da_confianca_alta():
    p = _prever([10, 200, 15, 180, 20, 190, 12, 170, 25, 160, 18, 185])

    assert p.confianca == "media"
    assert "oscila" in p.motivo_confianca


def test_historico_curto_da_confianca_baixa_com_motivo_legivel():
    p = _prever([100, 100])

    assert p.confianca == "baixa"
    assert "2 meses" in p.motivo_confianca


def test_item_sem_venda_no_historico_nao_quebra():
    """Divisão por zero é o jeito clássico de um cálculo de previsão derrubar
    a instância. Item com venda zero existe: produto que saiu do cardápio."""
    p = _prever([0, 0, 0, 0, 0, 0])

    assert p.demanda_prevista == 0.0
    assert p.sugestao_compra == 0.0
    assert p.confianca == "baixa"


# --------------------------------------------------------- alerta de volume
def test_mes_base_com_volume_muito_abaixo_gera_alerta():
    """O caso achado na base real: set/26 vendeu 75% da média e todo item
    apareceu em queda. Pode ser mês fraco de verdade ou export incompleto — o
    sistema não adivinha, avisa."""
    item_a = _serie([100, 100, 100, 100, 75])
    item_b = _serie([200, 200, 200, 200, 150])

    alerta = alerta_volume([item_a, item_b], periodo_base="2025-05")

    assert alerta is not None
    assert "abaixo" in alerta
    assert "25%" in alerta
    assert "incompleto" in alerta


def test_mes_base_com_volume_muito_acima_tambem_gera_alerta():
    alerta = alerta_volume([_serie([100, 100, 100, 100, 200])], periodo_base="2025-05")

    assert alerta is not None
    assert "acima" in alerta


def test_volume_dentro_do_padrao_nao_gera_alerta():
    # 105 contra mediana 100 = +5%, abaixo do limite de 20%
    assert alerta_volume([_serie([100, 100, 100, 100, 105])], periodo_base="2025-05") is None


def test_historico_curto_nao_gera_alerta_de_volume():
    """Com dois meses de referência, 'fora do padrão' não significa nada."""
    assert alerta_volume([_serie([100, 50])], periodo_base="2025-02") is None


def test_alerta_de_volume_sem_serie_nenhuma_nao_quebra():
    assert alerta_volume([], periodo_base="2026-09") is None


def test_historico_fora_de_ordem_e_ordenado_antes_do_calculo():
    desordenado = [
        Ponto(periodo="2026-03", quantidade=60),
        Ponto(periodo="2026-01", quantidade=300),
        Ponto(periodo="2026-02", quantidade=60),
    ]

    p = prever(
        nome="X",
        grupo="G",
        subgrupo=None,
        historico=desordenado,
        periodo_alvo="2026-04",
        margem_seguranca_pct=0,
    )

    assert [h.periodo for h in p.historico] == ["2026-01", "2026-02", "2026-03"]
    assert p.media_recente == 140.0  # (300 + 60 + 60) / 3
