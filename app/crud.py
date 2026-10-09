"""Operações de banco. As rotas chamam daqui — elas não montam query.

Separar assim deixa a regra testável sem subir servidor HTTP e evita que
`routers/` vire um arquivão com SQL no meio.
"""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Casa, ItemCusto, UploadCusto
from app.schemas import CasaCreate, CasaUpdate


# ------------------------------------------------------------------ Casa
def listar_casas(
    db: Session,
    *,
    limit: int = 50,
    offset: int = 0,
    ativa: bool | None = None,
    busca: str | None = None,
) -> tuple[int, list[Casa]]:
    """Devolve (total, página). O total é contado com os mesmos filtros."""
    stmt = select(Casa)

    if ativa is not None:
        stmt = stmt.where(Casa.ativa == ativa)
    if busca:
        stmt = stmt.where(Casa.nome.ilike(f"%{busca}%"))

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    casas = list(db.scalars(stmt.order_by(Casa.id).limit(limit).offset(offset)).all())
    return total, casas


def buscar_casa(db: Session, casa_id: int) -> Casa | None:
    """None quando não existe. Quem decide devolver 404 é a rota."""
    return db.get(Casa, casa_id)


def criar_casa(db: Session, dados: CasaCreate) -> Casa:
    casa = Casa(**dados.model_dump())
    db.add(casa)
    db.commit()
    db.refresh(casa)
    return casa


def atualizar_casa(db: Session, casa: Casa, dados: CasaUpdate) -> Casa:
    # exclude_unset: só o que o cliente realmente mandou. É o que faz o PATCH
    # ser PATCH — sem isso, campo omitido viraria None e apagaria dado.
    for campo, valor in dados.model_dump(exclude_unset=True).items():
        setattr(casa, campo, valor)
    db.commit()
    db.refresh(casa)
    return casa


def remover_casa(db: Session, casa: Casa) -> None:
    db.delete(casa)
    db.commit()


# -------------------------------------------------------- Upload de custo (RF01)
def registrar_upload_custo(
    db: Session,
    *,
    casa_id: int,
    periodo: str,
    nome_original: str,
    blob_name: str,
    content_type: str,
    tamanho_bytes: int,
    url: str,
    itens: list[dict],
) -> UploadCusto:
    upload = UploadCusto(
        casa_id=casa_id,
        periodo=periodo,
        nome_original=nome_original,
        blob_name=blob_name,
        content_type=content_type,
        tamanho_bytes=tamanho_bytes,
        url=url,
    )
    upload.itens = [
        ItemCusto(
            nome=item["nome"],
            custo_teorico=item["custo_teorico"],
            custo_real=item["custo_real"],
        )
        for item in itens
    ]
    db.add(upload)
    db.commit()
    db.refresh(upload)
    return upload


def listar_uploads_custo(
    db: Session, *, limit: int = 50, offset: int = 0, casa_id: int | None = None
) -> tuple[int, list[UploadCusto]]:
    stmt = select(UploadCusto)
    if casa_id is not None:
        stmt = stmt.where(UploadCusto.casa_id == casa_id)

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    uploads = list(
        db.scalars(stmt.order_by(UploadCusto.id.desc()).limit(limit).offset(offset)).all()
    )
    return total, uploads


# ------------------------------------------------------------------- Delta (RF02)
def calcular_delta(db: Session, casa_id: int, periodo: str) -> dict | None:
    """Agrega custo teórico x real por casa e período. Agregação no banco,
    não em Python — é o que `func.coalesce`/`func.sum` fazem aqui.

    `None` quando não há upload para a casa/período: quem decide o 404 com
    mensagem explicativa é a rota, não o crud.
    """
    uploads_ids = select(UploadCusto.id).where(
        UploadCusto.casa_id == casa_id, UploadCusto.periodo == periodo
    )

    total_teorico = db.scalar(
        select(func.coalesce(func.sum(ItemCusto.custo_teorico), 0)).where(
            ItemCusto.upload_id.in_(uploads_ids)
        )
    )
    total_real = db.scalar(
        select(func.coalesce(func.sum(ItemCusto.custo_real), 0)).where(
            ItemCusto.upload_id.in_(uploads_ids)
        )
    )

    if total_teorico is None and total_real is None:
        return None

    itens = list(
        db.scalars(
            select(ItemCusto)
            .where(ItemCusto.upload_id.in_(uploads_ids))
            .order_by(func.abs(ItemCusto.custo_real - ItemCusto.custo_teorico).desc())
        ).all()
    )
    if not itens:
        return None

    return {
        "custo_teorico_total": float(total_teorico or 0),
        "custo_real_total": float(total_real or 0),
        "itens": itens,
    }
