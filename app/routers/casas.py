"""CRUD completo de `Casa` (unidade do grupo) — RF08, o 1º item do MVP mínimo.

Convenções aplicadas (skill oficial do FastAPI):
  - parâmetros e dependências via `Annotated`, nunca `= Depends()` no default;
  - sem `...` (Ellipsis): obrigatoriedade vem de não haver default;
  - prefix / tags / responses declarados no próprio APIRouter;
  - `def` normal quando não há `await` dentro — o FastAPI joga em threadpool.
"""

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Response, status

from app import crud
from app.deps import DbSession, PaginacaoDep
from app.models import Casa
from app.schemas import CasaCreate, CasaPage, CasaResponse, CasaUpdate, ErroResponse

router = APIRouter(
    prefix="/api/v1/casas",  # versionar desde o começo permite evoluir sem quebrar cliente
    tags=["casas"],
    responses={404: {"model": ErroResponse, "description": "Casa não encontrada"}},
)

Ativa = Annotated[bool | None, Query(description="Filtra por casa ativa/inativa")]
Busca = Annotated[str | None, Query(min_length=2, description="Busca parcial no nome")]


def _obter_ou_404(db: DbSession, casa_id: int) -> Casa:
    casa = crud.buscar_casa(db, casa_id)
    if casa is None:
        # 404 e não 200 com null: devolver null obriga o frontend a adivinhar.
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Casa {casa_id} não encontrada",
        )
    return casa


@router.get("", summary="Listar casas")
def listar_casas(
    db: DbSession,
    pag: PaginacaoDep,
    ativa: Ativa = None,
    busca: Busca = None,
) -> CasaPage:
    total, casas = crud.listar_casas(
        db, limit=pag.limit, offset=pag.offset, ativa=ativa, busca=busca
    )
    return CasaPage(
        total=total,
        limit=pag.limit,
        offset=pag.offset,
        items=[CasaResponse.model_validate(c) for c in casas],
    )


@router.get("/{casa_id}", summary="Detalhar casa")
def buscar_casa(db: DbSession, casa_id: int) -> CasaResponse:
    # casa_id: int já garante 422 para /api/v1/casas/abc — sem escrever nada.
    return CasaResponse.model_validate(_obter_ou_404(db, casa_id))


@router.post("", status_code=status.HTTP_201_CREATED, summary="Criar casa")
def criar_casa(db: DbSession, dados: CasaCreate) -> CasaResponse:
    # 201, não 200: criou um recurso novo. POST não é idempotente — mandar duas
    # vezes cria duas casas, exatamente como o duplo clique do usuário.
    return CasaResponse.model_validate(crud.criar_casa(db, dados))


@router.patch("/{casa_id}", summary="Atualizar casa")
def atualizar_casa(db: DbSession, casa_id: int, dados: CasaUpdate) -> CasaResponse:
    casa = _obter_ou_404(db, casa_id)
    return CasaResponse.model_validate(crud.atualizar_casa(db, casa, dados))


@router.delete(
    "/{casa_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remover casa",
    responses={204: {"description": "Removida — sem corpo na resposta"}},
)
def remover_casa(db: DbSession, casa_id: int) -> Response:
    casa = _obter_ou_404(db, casa_id)
    crud.remover_casa(db, casa)
    # 204 No Content: apagou, não há o que devolver.
    return Response(status_code=status.HTTP_204_NO_CONTENT)
