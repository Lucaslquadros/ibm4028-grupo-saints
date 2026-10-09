"""Models = tabelas do banco (SQLAlchemy).

NÃO confunda com schemas.py (Pydantic). Aula 04, "a confusão número um":
  - Model  = como o dado é GUARDADO. Muda quando a modelagem do banco muda.
  - Schema = o que ENTRA e SAI da API. Muda quando o contrato com o front muda.

Expor o model direto na API vaza campo sensível e prende o banco ao formato da API.

>>> PLACEHOLDER <<<
`Item` é um domínio genérico de partida. Quando o cliente e o problema estiverem
definidos, renomeie para a entidade real do projeto (Pet, Doacao, Entrega, Aluno...)
e ajuste schemas.py, crud.py, routers/itens.py e os testes junto.
"""

from datetime import UTC, datetime

from sqlalchemy import DateTime, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Item(Base):
    __tablename__ = "itens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nome: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    descricao: Mapped[str | None] = mapped_column(Text, nullable=True)
    categoria: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    quantidade: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    valor: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)

    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    def __repr__(self) -> str:  # pragma: no cover - conveniência de debug
        return f"<Item id={self.id} nome={self.nome!r}>"


class Arquivo(Base):
    """Metadados de cada upload. O arquivo em si vai para o Blob Storage.

    Guardar o binário no banco relacional é caro e não escala — o padrão cloud é
    binário no object storage, ponteiro no banco.
    """

    __tablename__ = "arquivos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nome_original: Mapped[str] = mapped_column(String(255), nullable=False)
    blob_name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    content_type: Mapped[str] = mapped_column(String(120), nullable=False)
    tamanho_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    url: Mapped[str] = mapped_column(String(1000), nullable=False)

    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
