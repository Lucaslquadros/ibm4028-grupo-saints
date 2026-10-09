"""Schemas = contrato da API (Pydantic).

Declarar o tipo É escrever a validação — e a documentação junto.
Se o código dentro da função rodou, o dado já está válido. Não escreva `if`.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------- Item
class ItemBase(BaseModel):
    nome: str = Field(min_length=3, max_length=120, description="Nome do item")
    descricao: str | None = Field(default=None, max_length=2000)
    categoria: str = Field(min_length=2, max_length=60)
    quantidade: int = Field(ge=0, le=1_000_000, default=0)
    valor: float = Field(ge=0, default=0)


class ItemCreate(ItemBase):
    """O que o cliente ENVIA no POST. Não tem `id`: quem gera é o servidor."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "nome": "Ração Premium 15kg",
                    "descricao": "Ração seca para cães adultos",
                    "categoria": "alimentacao",
                    "quantidade": 24,
                    "valor": 189.90,
                }
            ]
        }
    )


class ItemUpdate(BaseModel):
    """PATCH: todos os campos opcionais. Só o que veio é alterado."""

    nome: str | None = Field(default=None, min_length=3, max_length=120)
    descricao: str | None = Field(default=None, max_length=2000)
    categoria: str | None = Field(default=None, min_length=2, max_length=60)
    quantidade: int | None = Field(default=None, ge=0, le=1_000_000)
    valor: float | None = Field(default=None, ge=0)


class ItemResponse(ItemBase):
    """O que a API DEVOLVE. from_attributes lê direto do objeto SQLAlchemy."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    criado_em: datetime
    atualizado_em: datetime


class ItemPage(BaseModel):
    """Resposta paginada. Nunca devolva uma tabela inteira sem limite."""

    total: int
    limit: int
    offset: int
    items: list[ItemResponse]


# ------------------------------------------------------------ Arquivos
class ArquivoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nome_original: str
    blob_name: str
    content_type: str
    tamanho_bytes: int
    url: str
    criado_em: datetime


# ------------------------------------------------------------- Métricas
class MetricaCategoria(BaseModel):
    categoria: str
    quantidade_itens: int
    quantidade_total: int
    valor_total: float


class ResumoDashboard(BaseModel):
    """Alimenta o dashboard do frontend — o 3º item do MVP mínimo."""

    total_itens: int
    valor_total_estoque: float
    quantidade_total: int
    por_categoria: list[MetricaCategoria]


# ------------------------------------------------------------ Health/Erro
class HealthResponse(BaseModel):
    status: str
    versao: str
    ambiente: str
    banco: str


class ErroResponse(BaseModel):
    """Formato único de erro da API — o frontend trata um só formato."""

    detail: str
