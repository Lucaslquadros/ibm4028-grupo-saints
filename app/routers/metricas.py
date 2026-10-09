"""Delta custo teórico x real — RF02, prioridade nº1 do cliente.

A agregação é feita no banco (SUM/GROUP BY via `crud.calcular_delta`), não em
Python. Trazer a tabela inteira para somar na aplicação funciona com 50 linhas
e derruba a instância com 500 mil.
"""

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query

from app import crud
from app.deps import DbSession
from app.schemas import PERIODO_PATTERN, DeltaCasaResponse, ErroResponse, ItemCustoResponse

router = APIRouter(prefix="/api/v1/metricas", tags=["metricas"])

CasaId = Annotated[int, Query(description="Id da casa")]
Periodo = Annotated[str, Query(pattern=PERIODO_PATTERN, description="Período no formato AAAA-MM")]


@router.get(
    "/delta",
    summary="Delta custo teórico x real de uma casa, por período",
    responses={
        404: {
            "model": ErroResponse,
            "description": "Casa não existe, ou não há upload para esse período",
        }
    },
)
def delta_por_casa(db: DbSession, casa_id: CasaId, periodo: Periodo) -> DeltaCasaResponse:
    casa = crud.buscar_casa(db, casa_id)
    if casa is None:
        raise HTTPException(status_code=404, detail=f"Casa {casa_id} não encontrada")

    resultado = crud.calcular_delta(db, casa_id, periodo)
    if resultado is None:
        # 404 com mensagem explícita do que falta — não um erro genérico, e
        # não 200 com zeros (que pareceria "sem perda" em vez de "sem dado").
        raise HTTPException(
            status_code=404,
            detail=f"Nenhum dado de custo encontrado para a casa {casa_id} no período {periodo}",
        )

    teorico_total = resultado["custo_teorico_total"]
    real_total = resultado["custo_real_total"]

    return DeltaCasaResponse(
        casa_id=casa.id,
        casa_nome=casa.nome,
        periodo=periodo,
        custo_teorico_total=teorico_total,
        custo_real_total=real_total,
        delta_total=real_total - teorico_total,
        itens=[
            ItemCustoResponse(
                id=item.id,
                nome=item.nome,
                custo_teorico=float(item.custo_teorico),
                custo_real=float(item.custo_real),
                delta=float(item.custo_real) - float(item.custo_teorico),
            )
            for item in resultado["itens"]
        ],
    )
