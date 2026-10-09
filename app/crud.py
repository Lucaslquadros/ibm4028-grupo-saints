"""Operações de banco. As rotas chamam daqui — elas não montam query.

Separar assim deixa a regra testável sem subir servidor HTTP e evita que
`routers/` vire um arquivão com SQL no meio.
"""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Arquivo, Item
from app.schemas import ItemCreate, ItemUpdate


# ------------------------------------------------------------------ Item
def listar_itens(
    db: Session,
    *,
    limit: int = 50,
    offset: int = 0,
    categoria: str | None = None,
    busca: str | None = None,
) -> tuple[int, list[Item]]:
    """Devolve (total, página). O total é contado com os mesmos filtros."""
    stmt = select(Item)

    if categoria:
        stmt = stmt.where(Item.categoria == categoria)
    if busca:
        stmt = stmt.where(Item.nome.ilike(f"%{busca}%"))

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    itens = list(db.scalars(stmt.order_by(Item.id).limit(limit).offset(offset)).all())
    return total, itens


def buscar_item(db: Session, item_id: int) -> Item | None:
    """None quando não existe. Quem decide devolver 404 é a rota."""
    return db.get(Item, item_id)


def criar_item(db: Session, dados: ItemCreate) -> Item:
    item = Item(**dados.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def atualizar_item(db: Session, item: Item, dados: ItemUpdate) -> Item:
    # exclude_unset: só o que o cliente realmente mandou. É o que faz o PATCH
    # ser PATCH — sem isso, campo omitido viraria None e apagaria dado.
    for campo, valor in dados.model_dump(exclude_unset=True).items():
        setattr(item, campo, valor)
    db.commit()
    db.refresh(item)
    return item


def remover_item(db: Session, item: Item) -> None:
    db.delete(item)
    db.commit()


# -------------------------------------------------------------- Métricas
def resumo_dashboard(db: Session) -> dict:
    total_itens = db.scalar(select(func.count(Item.id))) or 0
    quantidade_total = db.scalar(select(func.coalesce(func.sum(Item.quantidade), 0))) or 0
    valor_total = db.scalar(select(func.coalesce(func.sum(Item.quantidade * Item.valor), 0))) or 0

    linhas = db.execute(
        select(
            Item.categoria,
            func.count(Item.id),
            func.coalesce(func.sum(Item.quantidade), 0),
            func.coalesce(func.sum(Item.quantidade * Item.valor), 0),
        )
        .group_by(Item.categoria)
        .order_by(func.sum(Item.quantidade * Item.valor).desc())
    ).all()

    return {
        "total_itens": total_itens,
        "valor_total_estoque": float(valor_total),
        "quantidade_total": int(quantidade_total),
        "por_categoria": [
            {
                "categoria": cat,
                "quantidade_itens": int(n),
                "quantidade_total": int(qtd),
                "valor_total": float(val),
            }
            for cat, n, qtd, val in linhas
        ],
    }


# -------------------------------------------------------------- Arquivos
def registrar_arquivo(db: Session, **dados) -> Arquivo:
    arquivo = Arquivo(**dados)
    db.add(arquivo)
    db.commit()
    db.refresh(arquivo)
    return arquivo


def listar_arquivos(db: Session, limit: int = 50) -> list[Arquivo]:
    return list(db.scalars(select(Arquivo).order_by(Arquivo.id.desc()).limit(limit)).all())
