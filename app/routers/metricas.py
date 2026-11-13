"""Fechamento de CMV — RF02/RF04, prioridade nº1 do cliente.

Automatiza o relatório que a equipe de custos monta à mão todo mês, por casa
(~2 dias): CMV teórico (cardápio) × CMV real (compras), o ajuste entre os dois,
a evolução mês a mês e os itens que mais pesam.

A agregação é feita no banco (SUM/GROUP BY em `crud`), não em Python. Trazer a
tabela inteira para somar na aplicação funciona com 50 linhas e derruba a
instância com 500 mil.
"""

from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException, Query

from app import crud
from app.deps import DbSession
from app.schemas import (
    PERIODO_PATTERN,
    Acumulado,
    ErroResponse,
    Explicacao,
    FechamentoResponse,
    ItemCardapioResponse,
    LinhaFechamento,
    PontoEvolucao,
    PontoHistorico,
    PrevisaoItem,
    RecomendacaoCompraResponse,
)
from app.services import explicacao as servico_explicacao
from app.services import previsao as servico_previsao

router = APIRouter(
    prefix="/api/v1/metricas",
    tags=["metricas"],
    responses={404: {"model": ErroResponse}},
)

CasaId = Annotated[int, Query(description="Id da casa")]
Periodo = Annotated[str, Query(pattern=PERIODO_PATTERN, description="Período no formato AAAA-MM")]


def _casa_ou_404(db, casa_id: int):
    casa = crud.buscar_casa(db, casa_id)
    if casa is None:
        raise HTTPException(status_code=404, detail=f"Casa {casa_id} não encontrada")
    return casa


@router.get("/fechamento", summary="Fechamento de CMV de uma casa no mês")
def fechamento(db: DbSession, casa_id: CasaId, periodo: Periodo) -> FechamentoResponse:
    casa = _casa_ou_404(db, casa_id)
    resultado = crud.calcular_fechamento(db, casa_id, periodo)
    if resultado is None:
        # 404 com mensagem explícita do que falta — não 200 com zeros (que
        # pareceria "sem perda" em vez de "sem dado").
        raise HTTPException(
            status_code=404,
            detail=f"Nenhum relatório enviado para a casa {casa_id} no período {periodo}",
        )
    return FechamentoResponse(
        casa_id=casa.id,
        casa_nome=casa.nome,
        periodo=periodo,
        tem_cardapio=resultado["tem_cardapio"],
        tem_compras=resultado["tem_compras"],
        total=LinhaFechamento(**resultado["total"]),
        grupos=[LinhaFechamento(**g) for g in resultado["grupos"]],
        explicacao=_explicacao(db, casa_id, periodo, resultado),
        base_real=resultado["base_real"],
        acumulado=_acumulado(db, casa_id, periodo),
    )


def _acumulado(db, casa_id: int, periodo: str) -> Acumulado | None:
    dados = crud.fechamento_acumulado(db, casa_id, periodo)
    if dados is None:
        return None
    return Acumulado(
        **{
            **dados,
            "total": LinhaFechamento(**dados["total"]),
            "grupos": [LinhaFechamento(**g) for g in dados["grupos"]],
        }
    )


def _explicacao(db, casa_id: int, periodo: str, resultado: dict) -> Explicacao | None:
    """RF11 — a explicação do ajuste, ou None quando falta um dos dois lados.

    A consulta dos subgrupos só roda quando há o que comparar: mês com um lado
    só não gera explicação nenhuma (docs/11, 3.4), então nem vale a query.
    """
    if not (resultado["tem_cardapio"] and resultado["tem_compras"]):
        return None

    # A planilha-modelo é por grupo: sem subgrupo, a decomposição fica no grupo.
    # Buscar subgrupos aqui traria os de uploads antigos do Everest da casa.
    linhas = (
        []
        if resultado.get("fonte") == "planilha"
        else crud.subgrupos_por_lado(
            db, casa_id=casa_id, periodo=periodo, grupos=resultado["grupos_cmv"]
        )
    )
    dados = servico_explicacao.explicar(
        periodo=periodo,
        total=resultado["total"],
        grupos=resultado["grupos"],
        subgrupos=[
            servico_explicacao.LinhaSubgrupo(
                tipo=tipo, grupo=grupo, subgrupo=subgrupo, custo=custo, venda=venda
            )
            for tipo, grupo, subgrupo, custo, venda in linhas
        ],
        base_real=resultado["base_real"],
    )
    return Explicacao(**dados) if dados is not None else None


@router.get("/evolucao", summary="Evolução mensal do CMV teórico × real")
def evolucao(
    db: DbSession,
    casa_id: CasaId,
    limit: Annotated[int, Query(ge=1, le=120, description="Últimos N meses")] = 24,
) -> list[PontoEvolucao]:
    _casa_ou_404(db, casa_id)
    return [PontoEvolucao(**p) for p in crud.evolucao_cmv(db, casa_id, limit)]


@router.get("/recomendacao-compra", summary="Demanda esperada por item no próximo mês (RF07)")
def recomendacao_compra(
    db: DbSession,
    casa_id: CasaId,
    periodo: Periodo,
    margem_seguranca_pct: Annotated[
        float,
        Query(ge=0, le=100, description="Margem sobre a demanda prevista, em %"),
    ] = 10.0,
    limit: Annotated[int, Query(ge=1, le=50, description="Quantos itens retornar")] = 10,
) -> RecomendacaoCompraResponse:
    """RF07 — o "quanto comprar" que hoje sai do senso do chefe.

    Devolve os itens que mais pesam no custo com a demanda esperada para o mês
    seguinte a `periodo`, a partir do histórico de venda já carregado.

    A matemática (média móvel + tendência + sazonalidade) está em
    `app/services/previsao.py`, fora da rota e fora do banco, porque é a parte
    que precisa ser testada com números na mão.
    """
    casa = _casa_ou_404(db, casa_id)
    linhas = crud.historico_itens(db, casa_id=casa_id, periodo=periodo, limit_itens=limit)
    if not linhas:
        raise HTTPException(
            status_code=404,
            detail=(
                f"Sem histórico de venda por item para a casa {casa_id} até {periodo}. "
                "Envie ao menos um relatório de cardápio."
            ),
        )

    # Agrupa a série de cada item preservando a ordem de relevância do banco.
    series: dict[str, dict] = {}
    for nome, grupo, subgrupo, per, quantidade, _custo in linhas:
        item = series.setdefault(nome, {"grupo": grupo, "subgrupo": subgrupo, "pontos": []})
        if quantidade is not None:
            item["pontos"].append(servico_previsao.Ponto(periodo=per, quantidade=float(quantidade)))

    periodo_alvo = servico_previsao.proximo_periodo(periodo)
    previsoes = [
        servico_previsao.prever(
            nome=nome,
            grupo=dados["grupo"],
            subgrupo=dados["subgrupo"],
            historico=dados["pontos"],
            periodo_alvo=periodo_alvo,
            margem_seguranca_pct=margem_seguranca_pct,
        )
        for nome, dados in series.items()
        if dados["pontos"]
    ]

    return RecomendacaoCompraResponse(
        casa_id=casa.id,
        casa_nome=casa.nome,
        periodo_base=periodo,
        periodo_alvo=periodo_alvo,
        margem_seguranca_pct=margem_seguranca_pct,
        metodo=(
            "Média de venda dos últimos 3 meses, ajustada por tendência "
            "(últimas 3 observações contra as 3 anteriores) e por sazonalidade "
            "(o mesmo mês nos anos anteriores). Não é machine learning."
        ),
        aviso=(
            "Sugestão assume estoque inicial zero — o sistema lê relatórios de venda "
            "e compra, nunca uma contagem, então não sabe o que já está na prateleira. "
            "Subtraia o estoque atual antes de comprar."
        ),
        # Queda uniforme em todo o catálogo costuma ser relatório incompleto, não
        # mercado. O sistema não corrige — avisa, e quem decide julga.
        alerta_dado=servico_previsao.alerta_volume(
            [dados["pontos"] for dados in series.values()], periodo
        ),
        itens=[
            PrevisaoItem(
                nome=p.nome,
                grupo=p.grupo,
                subgrupo=p.subgrupo,
                meses_com_dado=p.meses_com_dado,
                media_recente=p.media_recente,
                tendencia_pct=p.tendencia_pct,
                indice_sazonal=p.indice_sazonal,
                demanda_prevista=p.demanda_prevista,
                sugestao_compra=p.sugestao_compra,
                confianca=p.confianca,
                motivo_confianca=p.motivo_confianca,
                historico=[
                    PontoHistorico(periodo=h.periodo, quantidade=h.quantidade) for h in p.historico
                ],
            )
            for p in previsoes
        ],
    )


@router.get("/top-itens", summary="Itens do cardápio que mais pesam no CMV")
def top_itens(
    db: DbSession,
    casa_id: CasaId,
    periodo: Periodo,
    ordem: Annotated[
        Literal["custo", "cmv"],
        Query(description="custo = maior custo total; cmv = maior custo ÷ venda"),
    ] = "custo",
    limit: Annotated[int, Query(ge=1, le=50)] = 10,
) -> list[ItemCardapioResponse]:
    _casa_ou_404(db, casa_id)
    itens = crud.top_itens_cardapio(db, casa_id=casa_id, periodo=periodo, ordem=ordem, limit=limit)
    return [
        ItemCardapioResponse(
            nome=i.nome,
            grupo=i.grupo,
            subgrupo=i.subgrupo,
            quantidade=float(i.quantidade) if i.quantidade is not None else None,
            venda_liquida=float(i.venda_liquida) if i.venda_liquida is not None else None,
            custo=float(i.custo),
            cmv_pct=(
                round(float(i.custo) / float(i.venda_liquida) * 100, 2) if i.venda_liquida else None
            ),
        )
        for i in itens
    ]
