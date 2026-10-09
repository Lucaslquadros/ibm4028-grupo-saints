"""Models = tabelas do banco (SQLAlchemy).

NÃO confunda com schemas.py (Pydantic). Aula 04, "a confusão número um":
  - Model  = como o dado é GUARDADO. Muda quando a modelagem do banco muda.
  - Schema = o que ENTRA e SAI da API. Muda quando o contrato com o front muda.

Expor o model direto na API vaza campo sensível e prende o banco ao formato da API.

Domínio real (retomada de 09/10/2026, substitui o placeholder `Item`/`Arquivo`):
cobre o Problema 1 do cliente (delta custo teórico x real, por casa) — ver
docs/01-requisitos.md, RF08/RF01/RF02.
"""

from datetime import UTC, datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Casa(Base):
    """Uma unidade (bar/restaurante) do grupo. RF08 — CRUD obrigatório do MVP."""

    __tablename__ = "casas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nome: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    marca: Mapped[str] = mapped_column(String(120), nullable=False)
    cidade: Mapped[str] = mapped_column(String(120), nullable=False)
    ativa: Mapped[bool] = mapped_column(default=True, nullable=False)

    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    uploads: Mapped[list["UploadCusto"]] = relationship(
        back_populates="casa", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:  # pragma: no cover - conveniência de debug
        return f"<Casa id={self.id} nome={self.nome!r}>"


class UploadCusto(Base):
    """Metadados de um export do Everest (RF01), associado a uma casa e período.

    O arquivo em si vai para o Blob Storage; aqui ficam só o ponteiro e os
    `ItemCusto` extraídos dele. Guardar o binário no banco relacional é caro e
    não escala — o padrão cloud é binário no object storage, ponteiro no banco.
    """

    __tablename__ = "uploads_custo"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    casa_id: Mapped[int] = mapped_column(ForeignKey("casas.id"), nullable=False, index=True)
    periodo: Mapped[str] = mapped_column(String(7), nullable=False, index=True)  # "AAAA-MM"

    nome_original: Mapped[str] = mapped_column(String(255), nullable=False)
    blob_name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    content_type: Mapped[str] = mapped_column(String(120), nullable=False)
    tamanho_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    url: Mapped[str] = mapped_column(String(1000), nullable=False)

    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    casa: Mapped["Casa"] = relationship(back_populates="uploads")
    itens: Mapped[list["ItemCusto"]] = relationship(
        back_populates="upload", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<UploadCusto id={self.id} casa_id={self.casa_id} periodo={self.periodo!r}>"


class ItemCusto(Base):
    """Uma linha do export: custo teórico x real de um insumo/prato (RF02).

    O delta (custo_real - custo_teorico) é calculado em cima destas linhas,
    agregado por casa e período — nunca somado em Python fora do banco.
    """

    __tablename__ = "itens_custo"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    upload_id: Mapped[int] = mapped_column(
        ForeignKey("uploads_custo.id"), nullable=False, index=True
    )
    nome: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    custo_teorico: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    custo_real: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)

    upload: Mapped["UploadCusto"] = relationship(back_populates="itens")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<ItemCusto id={self.id} nome={self.nome!r}>"
