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
    ErroResponse,
    FechamentoResponse,
    ItemCardapioResponse,
    LinhaFechamento,
    PontoEvolucao,
)

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
    )


@router.get("/evolucao", summary="Evolução mensal do CMV teórico × real")
def evolucao(
    db: DbSession,
    casa_id: CasaId,
    limit: Annotated[int, Query(ge=1, le=120, description="Últimos N meses")] = 24,
) -> list[PontoEvolucao]:
    _casa_ou_404(db, casa_id)
    return [PontoEvolucao(**p) for p in crud.evolucao_cmv(db, casa_id, limit)]


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
