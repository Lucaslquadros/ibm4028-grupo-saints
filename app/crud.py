"""Operações de banco. As rotas chamam daqui — elas não montam query.

Separar assim deixa a regra testável sem subir servidor HTTP e evita que
`routers/` vire um arquivão com SQL no meio.
"""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Casa, LinhaCusto, UploadCusto
from app.schemas import CasaCreate, CasaUpdate
from app.services.leitores import Linha


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
def buscar_upload_existente(
    db: Session, *, casa_id: int, periodo: str, tipo: str
) -> UploadCusto | None:
    return db.scalar(
        select(UploadCusto).where(
            UploadCusto.casa_id == casa_id,
            UploadCusto.periodo == periodo,
            UploadCusto.tipo == tipo,
        )
    )


def registrar_upload_custo(
    db: Session,
    *,
    casa_id: int,
    periodo: str,
    tipo: str,
    nome_original: str,
    blob_name: str,
    content_type: str,
    tamanho_bytes: int,
    url: str,
    linhas: list[Linha],
) -> UploadCusto:
    """Grava o upload e as linhas extraídas. Se já havia um upload da mesma
    casa/período/tipo, ele é substituído (reenviar o export corrige o mês).
    Quem apaga o blob antigo é a rota, depois do commit."""
    antigo = buscar_upload_existente(db, casa_id=casa_id, periodo=periodo, tipo=tipo)
    if antigo is not None:
        db.delete(antigo)
        db.flush()

    upload = UploadCusto(
        casa_id=casa_id,
        periodo=periodo,
        tipo=tipo,
        nome_original=nome_original,
        blob_name=blob_name,
        content_type=content_type,
        tamanho_bytes=tamanho_bytes,
        url=url,
    )
    upload.linhas = [
        LinhaCusto(
            nivel=linha.nivel,
            grupo=linha.grupo,
            subgrupo=linha.subgrupo,
            nome=linha.nome[:200],
            quantidade=linha.quantidade,
            venda_liquida=linha.venda_liquida,
            custo=linha.custo,
        )
        for linha in linhas
    ]
    db.add(upload)
    db.commit()
    db.refresh(upload)
    return upload


def contar_linhas(db: Session, upload_id: int) -> int:
    return (
        db.scalar(select(func.count(LinhaCusto.id)).where(LinhaCusto.upload_id == upload_id)) or 0
    )


def listar_uploads_custo(
    db: Session,
    *,
    limit: int = 50,
    offset: int = 0,
    casa_id: int | None = None,
    periodo: str | None = None,
) -> tuple[int, list[tuple[UploadCusto, int]]]:
    """Devolve (total, [(upload, nº de linhas)]). A contagem de linhas sai do
    banco num GROUP BY, não carregando as linhas de cada upload."""
    filtros = []
    if casa_id is not None:
        filtros.append(UploadCusto.casa_id == casa_id)
    if periodo is not None:
        filtros.append(UploadCusto.periodo == periodo)

    total = db.scalar(select(func.count(UploadCusto.id)).where(*filtros)) or 0
    stmt = (
        select(UploadCusto, func.count(LinhaCusto.id))
        .outerjoin(LinhaCusto, LinhaCusto.upload_id == UploadCusto.id)
        .where(*filtros)
        .group_by(UploadCusto.id)
        .order_by(UploadCusto.periodo.desc(), UploadCusto.id.desc())
        .limit(limit)
        .offset(offset)
    )
    return total, [(upload, n) for upload, n in db.execute(stmt).all()]


# --------------------------------------------------------- Fechamento de CMV
# Os grupos que formam o CMV direto. Só eles existem nos dois relatórios:
# a DRE tem também utensílios e material de consumo (custo indireto), e o
# cardápio tem serviços (couvert), que não têm custo de mercadoria.
GRUPOS_CMV = ("ALIMENTOS", "BEBIDAS")


def _somas_por_grupo(db: Session, casa_id: int, periodos: list[str] | None = None):
    """[(periodo, tipo, grupo, custo, venda)] somados no banco."""
    stmt = (
        select(
            UploadCusto.periodo,
            UploadCusto.tipo,
            LinhaCusto.grupo,
            func.sum(LinhaCusto.custo),
            func.sum(LinhaCusto.venda_liquida),
        )
        .join(UploadCusto, UploadCusto.id == LinhaCusto.upload_id)
        .where(
            UploadCusto.casa_id == casa_id,
            LinhaCusto.nivel == "grupo",
            LinhaCusto.grupo.in_(GRUPOS_CMV),
        )
        .group_by(UploadCusto.periodo, UploadCusto.tipo, LinhaCusto.grupo)
    )
    if periodos is not None:
        stmt = stmt.where(UploadCusto.periodo.in_(periodos))
    return db.execute(stmt).all()


def _receitas_compras(db: Session, casa_id: int, periodos: list[str] | None = None):
    """{periodo: receita líquida da DRE} — usada como denominador quando o
    cardápio do mês ainda não foi enviado."""
    stmt = (
        select(UploadCusto.periodo, LinhaCusto.venda_liquida)
        .join(UploadCusto, UploadCusto.id == LinhaCusto.upload_id)
        .where(
            UploadCusto.casa_id == casa_id,
            UploadCusto.tipo == "compras",
            LinhaCusto.nivel == "total",
        )
    )
    if periodos is not None:
        stmt = stmt.where(UploadCusto.periodo.in_(periodos))
    return {periodo: float(v) for periodo, v in db.execute(stmt).all() if v is not None}


def _pct(custo: float | None, venda: float | None) -> float | None:
    if custo is None or not venda:
        return None
    return round(custo / venda * 100, 2)


def _montar_linha(
    grupo: str, custo_teorico: float | None, custo_real: float | None, venda: float | None
) -> dict:
    teorico_pct = _pct(custo_teorico, venda)
    real_pct = _pct(custo_real, venda)
    ajuste = (
        round(custo_real - custo_teorico, 2)
        if custo_real is not None and custo_teorico is not None
        else None
    )
    ajuste_pp = (
        round(real_pct - teorico_pct, 2)
        if real_pct is not None and teorico_pct is not None
        else None
    )
    return {
        "grupo": grupo,
        "venda_liquida": round(venda, 2) if venda is not None else None,
        "custo_teorico": round(custo_teorico, 2) if custo_teorico is not None else None,
        "custo_real": round(custo_real, 2) if custo_real is not None else None,
        "cmv_teorico_pct": teorico_pct,
        "cmv_real_pct": real_pct,
        "ajuste": ajuste,
        "ajuste_pp": ajuste_pp,
    }


def _fechamentos(db: Session, casa_id: int, periodos: list[str] | None = None) -> dict:
    """{periodo: {"tem_cardapio", "tem_compras", "grupos": [...], "total": {...}}}

    Regra do cálculo (ver docs/07-fechamento-cmv.md):
      teórico = custo do grupo no cardápio (vendas × ficha técnica)
      real    = custo do grupo na DRE de compras (pós-inventário)
      CMV %   = custo ÷ venda líquida do grupo no cardápio — o MESMO
                denominador nos dois lados, para que a diferença em pontos
                percentuais seja só diferença de custo. Sem cardápio no mês,
                usa a receita líquida da DRE.
      ajuste  = real − teórico
    """
    somas: dict[str, dict] = {}
    for periodo, tipo, grupo, custo, venda in _somas_por_grupo(db, casa_id, periodos):
        mes = somas.setdefault(periodo, {})
        g = mes.setdefault(grupo, {"cardapio": None, "compras": None, "venda": None})
        g[tipo] = float(custo) if custo is not None else None
        if tipo == "cardapio" and venda is not None:
            g["venda"] = float(venda)

    receitas = _receitas_compras(db, casa_id, periodos)
    resultado = {}
    for periodo, grupos in somas.items():
        tem_cardapio = any(g["cardapio"] is not None for g in grupos.values())
        tem_compras = any(g["compras"] is not None for g in grupos.values())
        linhas = []
        tot_teorico = tot_real = tot_venda = None
        for nome in GRUPOS_CMV:
            g = grupos.get(nome)
            if g is None:
                continue
            venda = g["venda"]
            linhas.append(_montar_linha(nome, g["cardapio"], g["compras"], venda))
            if g["cardapio"] is not None:
                tot_teorico = (tot_teorico or 0) + g["cardapio"]
            if g["compras"] is not None:
                tot_real = (tot_real or 0) + g["compras"]
            if venda is not None:
                tot_venda = (tot_venda or 0) + venda

        if not tem_cardapio:
            # sem venda por grupo: CMV % só no total, sobre a receita da DRE
            tot_venda = receitas.get(periodo)
            for linha in linhas:
                linha["cmv_real_pct"] = None

        resultado[periodo] = {
            "tem_cardapio": tem_cardapio,
            "tem_compras": tem_compras,
            "grupos": linhas,
            "total": _montar_linha("TOTAL", tot_teorico, tot_real, tot_venda),
        }
    return resultado


def calcular_fechamento(db: Session, casa_id: int, periodo: str) -> dict | None:
    """None quando não há nenhum upload da casa no período — a rota decide o 404."""
    return _fechamentos(db, casa_id, [periodo]).get(periodo)


def evolucao_cmv(db: Session, casa_id: int, limit: int = 24) -> list[dict]:
    """Os últimos `limit` meses com dado, em ordem cronológica."""
    periodos = list(
        db.scalars(
            select(UploadCusto.periodo)
            .where(UploadCusto.casa_id == casa_id)
            .distinct()
            .order_by(UploadCusto.periodo.desc())
            .limit(limit)
        ).all()
    )
    if not periodos:
        return []
    fechamentos = _fechamentos(db, casa_id, periodos)
    return [
        {
            "periodo": periodo,
            "cmv_teorico_pct": fechamentos[periodo]["total"]["cmv_teorico_pct"],
            "cmv_real_pct": fechamentos[periodo]["total"]["cmv_real_pct"],
            "ajuste_pp": fechamentos[periodo]["total"]["ajuste_pp"],
        }
        for periodo in sorted(periodos)
        if periodo in fechamentos
    ]


def top_itens_cardapio(
    db: Session,
    *,
    casa_id: int,
    periodo: str,
    ordem: str = "custo",
    limit: int = 10,
    venda_minima: float = 500.0,
) -> list[LinhaCusto]:
    """Itens do cardápio que mais pesam no CMV teórico.

    ordem="custo": maior custo total (onde está o dinheiro)
    ordem="cmv":   maior custo ÷ venda (prato com margem ruim); ignora itens
                   com venda abaixo de `venda_minima`, que distorcem o %.
    """
    stmt = (
        select(LinhaCusto)
        .join(UploadCusto, UploadCusto.id == LinhaCusto.upload_id)
        .where(
            UploadCusto.casa_id == casa_id,
            UploadCusto.periodo == periodo,
            UploadCusto.tipo == "cardapio",
            LinhaCusto.nivel == "item",
        )
    )
    if ordem == "cmv":
        stmt = stmt.where(LinhaCusto.venda_liquida >= venda_minima).order_by(
            (LinhaCusto.custo / LinhaCusto.venda_liquida).desc()
        )
    else:
        stmt = stmt.order_by(LinhaCusto.custo.desc())
    return list(db.scalars(stmt.limit(limit)).all())
