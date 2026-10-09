"""Upload de arquivos — o 2º item do MVP mínimo.

O binário vai para o Blob Storage; o banco guarda só os metadados e a URL.
Guardar binário em banco relacional é caro e não escala: o padrão cloud é
objeto no storage, ponteiro no banco.
"""

from typing import Annotated

from fastapi import APIRouter, File, HTTPException, UploadFile, status

from app import crud
from app.deps import AppSettings, DbSession
from app.schemas import ArquivoResponse
from app.services import storage

router = APIRouter(prefix="/api/v1/arquivos", tags=["arquivos"])

TIPOS_PERMITIDOS = frozenset(
    {
        "text/csv",
        "application/vnd.ms-excel",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/pdf",
        "image/png",
        "image/jpeg",
        "image/webp",
    }
)

ArquivoEnviado = Annotated[UploadFile, File(description="CSV, PDF ou imagem")]


@router.post("", status_code=status.HTTP_201_CREATED, summary="Enviar arquivo")
async def enviar_arquivo(
    db: DbSession,
    settings: AppSettings,
    arquivo: ArquivoEnviado,
) -> ArquivoResponse:
    # async def aqui é correto: existe `await arquivo.read()` dentro.
    if arquivo.content_type not in TIPOS_PERMITIDOS:
        # 415: o servidor entendeu a requisição, mas não aceita esse formato.
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Tipo '{arquivo.content_type}' não permitido. "
            f"Aceitos: {sorted(TIPOS_PERMITIDOS)}",
        )

    conteudo = await arquivo.read()

    if len(conteudo) > settings.max_upload_mb * 1024 * 1024:
        # 413: valide o tamanho ANTES de mandar para o Blob — upload rejeitado
        # depois de subido já custou banda e armazenamento.
        raise HTTPException(
            status_code=413,  # Content Too Large
            detail=f"Arquivo excede o limite de {settings.max_upload_mb} MB",
        )
    if not conteudo:
        raise HTTPException(status_code=422, detail="Arquivo vazio")

    blob_name, url = storage.salvar(conteudo, arquivo.filename or "sem-nome", arquivo.content_type)

    return ArquivoResponse.model_validate(
        crud.registrar_arquivo(
            db,
            nome_original=arquivo.filename or "sem-nome",
            blob_name=blob_name,
            content_type=arquivo.content_type,
            tamanho_bytes=len(conteudo),
            url=url,
        )
    )


@router.get("", summary="Listar arquivos")
def listar_arquivos(db: DbSession) -> list[ArquivoResponse]:
    return [ArquivoResponse.model_validate(a) for a in crud.listar_arquivos(db)]
