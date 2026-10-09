"""Upload do export de custo do Everest — RF01, o 2º item do MVP mínimo.

O binário vai para o Blob Storage; o banco guarda os metadados do upload e os
`ItemCusto` extraídos do CSV, associados à casa e ao período informados.
Guardar binário em banco relacional é caro e não escala: o padrão cloud é
objeto no storage, ponteiro no banco.
"""

import csv
import io
from typing import Annotated

from fastapi import APIRouter, Form, HTTPException, UploadFile, status

from app import crud
from app.deps import AppSettings, DbSession, PaginacaoDep
from app.schemas import PERIODO_PATTERN, UploadCustoPage, UploadCustoResponse
from app.services import storage

router = APIRouter(prefix="/api/v1/uploads-custo", tags=["uploads-custo"])

TIPOS_PERMITIDOS = frozenset(
    {
        "text/csv",
        "application/vnd.ms-excel",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    }
)

COLUNAS_OBRIGATORIAS = ("item", "custo_teorico", "custo_real")

CasaIdForm = Annotated[int, Form(description="Id da casa a que este export pertence")]
PeriodoForm = Annotated[
    str, Form(pattern=PERIODO_PATTERN, description="Período no formato AAAA-MM")
]


def _parsear_csv(conteudo: bytes) -> list[dict]:
    """Lê o export em linhas de `ItemCusto`. 422 (não 500) em qualquer
    formato inesperado — é dado que vem de fora, nunca confie nele sem checar.
    """
    texto = conteudo.decode("utf-8-sig", errors="replace")
    leitor = csv.DictReader(io.StringIO(texto))

    colunas = {c.strip().lower() for c in (leitor.fieldnames or [])}
    faltando = [c for c in COLUNAS_OBRIGATORIAS if c not in colunas]
    if faltando:
        raise HTTPException(
            status_code=422,
            detail=f"Coluna(s) obrigatória(s) faltando no CSV: {', '.join(faltando)}",
        )

    itens = []
    for numero_linha, linha in enumerate(leitor, start=2):  # linha 1 é o header
        linha = {k.strip().lower(): v for k, v in linha.items()}
        try:
            itens.append(
                {
                    "nome": linha["item"].strip(),
                    "custo_teorico": float(linha["custo_teorico"]),
                    "custo_real": float(linha["custo_real"]),
                }
            )
        except (ValueError, AttributeError, KeyError) as exc:
            raise HTTPException(
                status_code=422,
                detail=f"Linha {numero_linha} do CSV é inválida: {exc}",
            ) from exc

    if not itens:
        raise HTTPException(status_code=422, detail="CSV não tem nenhuma linha de dado")

    return itens


@router.post("", status_code=status.HTTP_201_CREATED, summary="Enviar export de custo do Everest")
async def enviar_upload_custo(
    db: DbSession,
    settings: AppSettings,
    casa_id: CasaIdForm,
    periodo: PeriodoForm,
    arquivo: UploadFile,
) -> UploadCustoResponse:
    # async def aqui é correto: existe `await arquivo.read()` dentro.
    if crud.buscar_casa(db, casa_id) is None:
        raise HTTPException(status_code=404, detail=f"Casa {casa_id} não encontrada")

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

    itens = _parsear_csv(conteudo)

    blob_name, url = storage.salvar(conteudo, arquivo.filename or "sem-nome", arquivo.content_type)

    upload = crud.registrar_upload_custo(
        db,
        casa_id=casa_id,
        periodo=periodo,
        nome_original=arquivo.filename or "sem-nome",
        blob_name=blob_name,
        content_type=arquivo.content_type,
        tamanho_bytes=len(conteudo),
        url=url,
        itens=itens,
    )

    return UploadCustoResponse(
        **{
            "id": upload.id,
            "casa_id": upload.casa_id,
            "periodo": upload.periodo,
            "nome_original": upload.nome_original,
            "blob_name": upload.blob_name,
            "content_type": upload.content_type,
            "tamanho_bytes": upload.tamanho_bytes,
            "url": upload.url,
            "criado_em": upload.criado_em,
            "itens_importados": len(upload.itens),
        }
    )


@router.get("", summary="Listar uploads de custo")
def listar_uploads_custo(
    db: DbSession, pag: PaginacaoDep, casa_id: int | None = None
) -> UploadCustoPage:
    total, uploads = crud.listar_uploads_custo(
        db, limit=pag.limit, offset=pag.offset, casa_id=casa_id
    )
    return UploadCustoPage(
        total=total,
        limit=pag.limit,
        offset=pag.offset,
        items=[
            UploadCustoResponse(
                id=u.id,
                casa_id=u.casa_id,
                periodo=u.periodo,
                nome_original=u.nome_original,
                blob_name=u.blob_name,
                content_type=u.content_type,
                tamanho_bytes=u.tamanho_bytes,
                url=u.url,
                criado_em=u.criado_em,
                itens_importados=len(u.itens),
            )
            for u in uploads
        ],
    )
