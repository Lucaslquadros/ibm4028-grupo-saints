"""Métricas agregadas que alimentam o dashboard — o 3º item do MVP mínimo.

A agregação é feita no banco (GROUP BY), não em Python. Trazer a tabela inteira
para somar na aplicação funciona com 50 linhas e derruba a instância com 500 mil.
"""

from fastapi import APIRouter

from app import crud
from app.deps import DbSession
from app.schemas import ResumoDashboard

router = APIRouter(prefix="/api/v1/metricas", tags=["metricas"])


@router.get("/resumo", summary="Resumo do dashboard")
def resumo(db: DbSession) -> ResumoDashboard:
    return ResumoDashboard(**crud.resumo_dashboard(db))
