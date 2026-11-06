"""Models = tabelas do banco (SQLAlchemy).

NÃO confunda com schemas.py (Pydantic). Aula 04, "a confusão número um":
  - Model  = como o dado é GUARDADO. Muda quando a modelagem do banco muda.
  - Schema = o que ENTRA e SAI da API. Muda quando o contrato com o front muda.

Expor o model direto na API vaza campo sensível e prende o banco ao formato da API.

Domínio real (retomada de 09/10/2026, substitui o placeholder `Item`/`Arquivo`):
cobre o Problema 1 do cliente (delta custo teórico x real, por casa) — ver
docs/01-requisitos.md, RF08/RF01/RF02.

Atualizado em 03/11/2026: `ItemCusto` (CSV fictício com custo teórico e real
na mesma linha) deu lugar a `LinhaCusto`. Os exports reais do Everest trazem
teórico e real em relatórios separados — ver docs/07-fechamento-cmv.md.
"""

from datetime import UTC, datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
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

    O arquivo em si vai para o Blob Storage; aqui ficam só o ponteiro e as
    `LinhaCusto` extraídas dele. Guardar o binário no banco relacional é caro e
    não escala — o padrão cloud é binário no object storage, ponteiro no banco.

    `tipo` diz qual relatório é — e portanto qual lado do fechamento ele alimenta:
      - "cardapio": engenharia de cardápio → CMV teórico (vendas × ficha técnica)
      - "compras":  DRE gerencial de compras → CMV real (pós-inventário)
    Há no máximo um upload por (casa, período, tipo): reenviar substitui o anterior.
    """

    __tablename__ = "uploads_custo"
    __table_args__ = (
        UniqueConstraint("casa_id", "periodo", "tipo", name="uq_upload_casa_periodo_tipo"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    casa_id: Mapped[int] = mapped_column(ForeignKey("casas.id"), nullable=False, index=True)
    periodo: Mapped[str] = mapped_column(String(7), nullable=False, index=True)  # "AAAA-MM"
    tipo: Mapped[str] = mapped_column(String(20), nullable=False, index=True)

    nome_original: Mapped[str] = mapped_column(String(255), nullable=False)
    blob_name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    content_type: Mapped[str] = mapped_column(String(120), nullable=False)
    tamanho_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    url: Mapped[str] = mapped_column(String(1000), nullable=False)

    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    casa: Mapped["Casa"] = relationship(back_populates="uploads")
    linhas: Mapped[list["LinhaCusto"]] = relationship(
        back_populates="upload", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<UploadCusto id={self.id} casa_id={self.casa_id} "
            f"periodo={self.periodo!r} tipo={self.tipo!r}>"
        )


class LinhaCusto(Base):
    """Uma linha extraída de um export, já traduzida para o formato único.

    Os dois relatórios do Everest têm layouts diferentes, mas os dois
    tradutores (`app/services/leitores.py`) produzem esta mesma linha. É isso
    que permite cruzar cardápio × compras com um GROUP BY.

    `nivel`:
      - "total":    total do relatório (venda/receita líquida e custo total)
      - "grupo":    ALIMENTOS, BEBIDAS…
      - "subgrupo": PETISCOS, CHOPP… (cardápio) / BOVINOS, CHOPP… (compras)
      - "item":     um produto vendido (só existe no cardápio)
    """

    __tablename__ = "linhas_custo"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    upload_id: Mapped[int] = mapped_column(
        ForeignKey("uploads_custo.id"), nullable=False, index=True
    )
    nivel: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    grupo: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    subgrupo: Mapped[str | None] = mapped_column(String(120), nullable=True)
    nome: Mapped[str] = mapped_column(String(200), nullable=False)
    quantidade: Mapped[float | None] = mapped_column(Numeric(14, 3), nullable=True)
    venda_liquida: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)
    custo: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False, default=0)

    upload: Mapped["UploadCusto"] = relationship(back_populates="linhas")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<LinhaCusto id={self.id} nivel={self.nivel!r} nome={self.nome!r}>"
