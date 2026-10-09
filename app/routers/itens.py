"""CRUD completo do recurso placeholder `Item` — o 1º item do MVP mínimo.

Ao trocar o domínio, este arquivo é o molde: mesma estrutura, mesmos status
codes, mesma paginação. Não invente um padrão diferente por recurso.

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
from app.models import Item
from app.schemas import ErroResponse, ItemCreate, ItemPage, ItemResponse, ItemUpdate

router = APIRouter(
    prefix="/api/v1/itens",  # versionar desde o começo permite evoluir sem quebrar cliente
    tags=["itens"],
    responses={404: {"model": ErroResponse, "description": "Item não encontrado"}},
)

Categoria = Annotated[str | None, Query(description="Filtra por categoria exata")]
Busca = Annotated[str | None, Query(min_length=2, description="Busca parcial no nome")]


def _obter_ou_404(db: DbSession, item_id: int) -> Item:
    item = crud.buscar_item(db, item_id)
    if item is None:
        # 404 e não 200 com null: devolver null obriga o frontend a adivinhar.
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Item {item_id} não encontrado",
        )
    return item


@router.get("", summary="Listar itens")
def listar_itens(
    db: DbSession,
    pag: PaginacaoDep,
    categoria: Categoria = None,
    busca: Busca = None,
) -> ItemPage:
    total, itens = crud.listar_itens(
        db, limit=pag.limit, offset=pag.offset, categoria=categoria, busca=busca
    )
    return ItemPage(
        total=total,
        limit=pag.limit,
        offset=pag.offset,
        items=[ItemResponse.model_validate(i) for i in itens],
    )


@router.get("/{item_id}", summary="Detalhar item")
def buscar_item(db: DbSession, item_id: int) -> ItemResponse:
    # item_id: int já garante 422 para /api/v1/itens/abc — sem escrever nada.
    return ItemResponse.model_validate(_obter_ou_404(db, item_id))


@router.post("", status_code=status.HTTP_201_CREATED, summary="Criar item")
def criar_item(db: DbSession, dados: ItemCreate) -> ItemResponse:
    # 201, não 200: criou um recurso novo. POST não é idempotente — mandar duas
    # vezes cria dois itens, exatamente como o duplo clique do usuário.
    return ItemResponse.model_validate(crud.criar_item(db, dados))


@router.patch("/{item_id}", summary="Atualizar item")
def atualizar_item(db: DbSession, item_id: int, dados: ItemUpdate) -> ItemResponse:
    item = _obter_ou_404(db, item_id)
    return ItemResponse.model_validate(crud.atualizar_item(db, item, dados))


@router.delete(
    "/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remover item",
    responses={204: {"description": "Removido — sem corpo na resposta"}},
)
def remover_item(db: DbSession, item_id: int) -> Response:
    item = _obter_ou_404(db, item_id)
    crud.remover_item(db, item)
    # 204 No Content: apagou, não há o que devolver.
    return Response(status_code=status.HTTP_204_NO_CONTENT)
