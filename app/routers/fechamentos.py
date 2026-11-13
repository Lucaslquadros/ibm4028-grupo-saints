"""Envio da planilha-modelo de fechamento (12/11/2026).

Um arquivo traz um mês ou vários, com os dois lados juntos e o movimento de
estoque — o período vem **no arquivo**, não no formulário. Com o estoque, o
lado real é o CMV real (EI + compras − EF). O caminho antigo
(`/uploads-custo`, um relatório do Everest por lado por mês) continua de pé.

Fluxo igual ao de `/uploads-custo`: valida (tipo, tamanho) → lê e valida a
planilha → confere no banco o estoque de abertura → grava o original no Blob →
grava os movimentos. Tudo o que pode recusar o arquivo vem antes do Blob.
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Form, HTTPException, Query, UploadFile, status

from app import crud
from app.deps import AppSettings, DbSession, PaginacaoDep
from app.schemas import ErroResponse, UploadFechamentoPage, UploadFechamentoResponse
from app.services import storage
from app.services.leitor_fechamento import ler_fechamento
from app.services.leitores import XLSX, ErroLeitura

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/fechamentos",
    tags=["fechamentos"],
    responses={404: {"model": ErroResponse}, 422: {"model": ErroResponse}},
)

TIPOS_PERMITIDOS = frozenset({XLSX, "application/octet-stream"})

CasaIdForm = Annotated[int, Form(description="Id da casa a que a planilha pertence")]


def _resposta(
    upload, periodos: list[str], linhas: int, substituidos: list[str] | None = None
) -> UploadFechamentoResponse:
    return UploadFechamentoResponse(
        id=upload.id,
        casa_id=upload.casa_id,
        nome_original=upload.nome_original,
        blob_name=upload.blob_name,
        content_type=upload.content_type,
        tamanho_bytes=upload.tamanho_bytes,
        url=upload.url,
        criado_em=upload.criado_em,
        periodos=periodos,
        linhas_importadas=linhas,
        meses_substituidos=substituidos or [],
    )


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="Enviar a planilha-modelo de fechamento (um ou vários meses)",
    responses={413: {"model": ErroResponse}, 415: {"model": ErroResponse}},
)
async def enviar_planilha_fechamento(
    db: DbSession,
    settings: AppSettings,
    casa_id: CasaIdForm,
    arquivo: UploadFile,
) -> UploadFechamentoResponse:
    if crud.buscar_casa(db, casa_id) is None:
        raise HTTPException(status_code=404, detail=f"Casa {casa_id} não encontrada")

    nome = arquivo.filename or "sem-nome.xlsx"
    if arquivo.content_type not in TIPOS_PERMITIDOS or not nome.lower().endswith(".xlsx"):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Envie a planilha de fechamento em Excel (.xlsx). "
            f"Recebido: '{nome}' ({arquivo.content_type}).",
        )

    conteudo = await arquivo.read()
    if len(conteudo) > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(
            status_code=413,  # Content Too Large
            detail=f"Arquivo excede o limite de {settings.max_upload_mb} MB",
        )
    if not conteudo:
        raise HTTPException(status_code=422, detail="Arquivo vazio")

    try:
        movimentos = ler_fechamento(conteudo)
    except ErroLeitura as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    sem_abertura = crud.meses_sem_estoque_inicial(db, casa_id, movimentos)
    if sem_abertura:
        lista = "; ".join(f"{m.grupo} em {m.periodo}" for m in sem_abertura[:10])
        raise HTTPException(
            status_code=422,
            detail=(
                f"Falta o estoque_inicial de: {lista}. Preencha o estoque_inicial ou inclua "
                "o mês anterior no arquivo — não há estoque_final desse mês enviado antes."
            ),
        )

    blob_name, url = storage.salvar(conteudo, nome, arquivo.content_type or XLSX)
    upload, substituidos, blobs_orfaos = crud.registrar_upload_fechamento(
        db,
        casa_id=casa_id,
        nome_original=nome,
        blob_name=blob_name,
        content_type=arquivo.content_type or XLSX,
        tamanho_bytes=len(conteudo),
        url=url,
        movimentos=movimentos,
    )

    for blob in blobs_orfaos:
        try:
            storage.remover(blob)
        except Exception:  # noqa: BLE001 - blob órfão não deve derrubar o upload
            logger.exception("Falha ao remover blob substituído %s", blob)

    periodos = sorted({m.periodo for m in movimentos})
    return _resposta(upload, periodos, len(movimentos), substituidos)


@router.get("", summary="Listar envios da planilha de fechamento")
def listar_planilhas_fechamento(
    db: DbSession,
    pag: PaginacaoDep,
    casa_id: Annotated[int | None, Query(description="Filtra por casa")] = None,
) -> UploadFechamentoPage:
    total, uploads = crud.listar_uploads_fechamento(
        db, casa_id=casa_id, limit=pag.limit, offset=pag.offset
    )
    return UploadFechamentoPage(
        total=total,
        limit=pag.limit,
        offset=pag.offset,
        items=[_resposta(u, meses, n) for u, meses, n in uploads],
    )
