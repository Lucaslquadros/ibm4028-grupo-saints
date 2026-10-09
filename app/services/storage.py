"""Abstração do armazenamento de arquivos.

Sem connection string configurada, grava em ./uploads_local/ — assim o time
desenvolve e roda os testes sem depender de credencial do Azure. Basta preencher
AZURE_STORAGE_CONNECTION_STRING no .env / App Settings para passar a usar o Blob,
sem alterar nenhuma linha das rotas.
"""

from __future__ import annotations

import uuid
from pathlib import Path

from app.config import settings

PASTA_LOCAL = Path("uploads_local")


def _nome_unico(nome_original: str) -> str:
    """Nunca confie no nome enviado pelo cliente.

    Reaproveitar o nome original permite sobrescrever arquivo alheio e abre
    path traversal (`../../etc/passwd`). Geramos um nome novo e guardamos o
    original apenas como metadado.
    """
    sufixo = Path(nome_original).suffix.lower()[:10]
    return f"{uuid.uuid4().hex}{sufixo}"


def usando_azure() -> bool:
    return bool(settings.azure_storage_connection_string)


def salvar(conteudo: bytes, nome_original: str, content_type: str) -> tuple[str, str]:
    """Grava o arquivo e devolve (blob_name, url)."""
    blob_name = _nome_unico(nome_original)

    if not usando_azure():
        PASTA_LOCAL.mkdir(parents=True, exist_ok=True)
        destino = PASTA_LOCAL / blob_name
        destino.write_bytes(conteudo)
        return blob_name, f"file://{destino.resolve()}"

    # Import tardio: quem roda só local não precisa do SDK carregado na memória.
    from azure.storage.blob import BlobServiceClient, ContentSettings

    service = BlobServiceClient.from_connection_string(settings.azure_storage_connection_string)
    container = service.get_container_client(settings.azure_storage_container)
    try:
        container.create_container()
    except Exception:  # noqa: BLE001 - container já existe é o caso normal
        pass

    blob = container.get_blob_client(blob_name)
    blob.upload_blob(
        conteudo,
        overwrite=False,
        content_settings=ContentSettings(content_type=content_type),
    )
    return blob_name, blob.url


def remover(blob_name: str) -> None:
    if not usando_azure():
        (PASTA_LOCAL / blob_name).unlink(missing_ok=True)
        return

    from azure.storage.blob import BlobServiceClient

    service = BlobServiceClient.from_connection_string(settings.azure_storage_connection_string)
    service.get_blob_client(container=settings.azure_storage_container, blob=blob_name).delete_blob(
        delete_snapshots="include"
    )
