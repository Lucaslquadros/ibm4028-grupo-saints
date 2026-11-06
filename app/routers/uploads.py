"""Upload dos exports do Everest — RF01, o 2º item do MVP mínimo.

Fluxo: valida (tipo, tamanho) → traduz o Excel para `LinhaCusto` → grava o
original no Blob → grava as linhas no banco. A tradução vem ANTES do Blob:
arquivo que não conseguimos ler é rejeitado sem custar armazenamento.

Dois tipos de relatório, um por lado do fechamento:
  - cardapio: engenharia de cardápio → CMV teórico
  - compras:  DRE gerencial de compras → CMV real
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Form, HTTPException, Query, UploadFile, status

from app import crud
from app.deps import AppSettings, DbSession, PaginacaoDep
from app.schemas import (
    PERIODO_PATTERN,
    ErroResponse,
    TipoUpload,
    UploadCustoPage,
    UploadCustoResponse,
)
from app.services import storage
from app.services.leitores import LEITORES, ErroLeitura

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/uploads-custo",
    tags=["uploads-custo"],
    responses={404: {"model": ErroResponse}, 422: {"model": ErroResponse}},
)

XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
# Alguns navegadores/SOs mandam .xlsx como octet-stream; aceitamos se a
# extensão for .xlsx — o tradutor recusa (422) se o conteúdo não for planilha.
TIPOS_PERMITIDOS = frozenset({XLSX, "application/octet-stream"})

CasaIdForm = Annotated[int, Form(description="Id da casa a que este export pertence")]
PeriodoForm = Annotated[
    str, Form(pattern=PERIODO_PATTERN, description="Período no formato AAAA-MM")
]
TipoForm = Annotated[
    TipoUpload,
    Form(description="cardapio = engenharia de cardápio; compras = DRE gerencial de compras"),
]


def _resposta(upload, linhas: int, substituiu: bool = False) -> UploadCustoResponse:
    return UploadCustoResponse(
        id=upload.id,
        casa_id=upload.casa_id,
        periodo=upload.periodo,
        tipo=upload.tipo,
        nome_original=upload.nome_original,
        blob_name=upload.blob_name,
        content_type=upload.content_type,
        tamanho_bytes=upload.tamanho_bytes,
        url=upload.url,
        criado_em=upload.criado_em,
        linhas_importadas=linhas,
        substituiu_anterior=substituiu,
    )


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="Enviar export do Everest (cardápio ou compras)",
    responses={413: {"model": ErroResponse}, 415: {"model": ErroResponse}},
)
async def enviar_upload_custo(
    db: DbSession,
    settings: AppSettings,
    casa_id: CasaIdForm,
    periodo: PeriodoForm,
    tipo: TipoForm,
    arquivo: UploadFile,
) -> UploadCustoResponse:
    # async def aqui é correto: existe `await arquivo.read()` dentro.
    if crud.buscar_casa(db, casa_id) is None:
        raise HTTPException(status_code=404, detail=f"Casa {casa_id} não encontrada")

    nome = arquivo.filename or "sem-nome.xlsx"
    if arquivo.content_type not in TIPOS_PERMITIDOS or not nome.lower().endswith(".xlsx"):
        # 415: o servidor entendeu a requisição, mas não aceita esse formato.
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Envie o export do Everest em Excel (.xlsx). "
            f"Recebido: '{nome}' ({arquivo.content_type}).",
        )

    conteudo = await arquivo.read()

    if len(conteudo) > settings.max_upload_mb * 1024 * 1024:
        # 413: valide o tamanho ANTES de mandar para o Blob.
        raise HTTPException(
            status_code=413,  # Content Too Large
            detail=f"Arquivo excede o limite de {settings.max_upload_mb} MB",
        )
    if not conteudo:
        raise HTTPException(status_code=422, detail="Arquivo vazio")

    try:
        extracao = LEITORES[tipo](conteudo, periodo)
    except ErroLeitura as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    anterior = crud.buscar_upload_existente(db, casa_id=casa_id, periodo=periodo, tipo=tipo)
    blob_antigo = anterior.blob_name if anterior else None

    blob_name, url = storage.salvar(conteudo, nome, arquivo.content_type or XLSX)

    upload = crud.registrar_upload_custo(
        db,
        casa_id=casa_id,
        periodo=periodo,
        tipo=tipo,
        nome_original=nome,
        blob_name=blob_name,
        content_type=arquivo.content_type or XLSX,
        tamanho_bytes=len(conteudo),
        url=url,
        linhas=extracao.linhas,
    )

    if blob_antigo:
        try:
            storage.remover(blob_antigo)
        except Exception:  # noqa: BLE001 - blob órfão não deve derrubar o upload
            logger.exception("Falha ao remover blob substituído %s", blob_antigo)

    return _resposta(upload, len(extracao.linhas), substituiu=blob_antigo is not None)


@router.get("", summary="Listar uploads de custo")
def listar_uploads_custo(
    db: DbSession,
    pag: PaginacaoDep,
    casa_id: int | None = None,
    periodo: Annotated[str | None, Query(pattern=PERIODO_PATTERN)] = None,
) -> UploadCustoPage:
    total, uploads = crud.listar_uploads_custo(
        db, limit=pag.limit, offset=pag.offset, casa_id=casa_id, periodo=periodo
    )
    return UploadCustoPage(
        total=total,
        limit=pag.limit,
        offset=pag.offset,
        items=[_resposta(upload, n) for upload, n in uploads],
    )
