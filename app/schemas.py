"""Schemas = contrato da API (Pydantic).

Declarar o tipo É escrever a validação — e a documentação junto.
Se o código dentro da função rodou, o dado já está válido. Não escreva `if`.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

PERIODO_PATTERN = r"^\d{4}-(0[1-9]|1[0-2])$"  # "AAAA-MM"


# ------------------------------------------------------------------ Casa
class CasaBase(BaseModel):
    nome: str = Field(min_length=3, max_length=120, description="Nome da casa")
    marca: str = Field(min_length=2, max_length=120)
    cidade: str = Field(min_length=2, max_length=120)
    ativa: bool = True


class CasaCreate(CasaBase):
    """O que o cliente ENVIA no POST. Não tem `id`: quem gera é o servidor."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "nome": "Boteco São Bento - Itaim",
                    "marca": "Boteco São Bento",
                    "cidade": "São Paulo",
                    "ativa": True,
                }
            ]
        }
    )


class CasaUpdate(BaseModel):
    """PATCH: todos os campos opcionais. Só o que veio é alterado."""

    nome: str | None = Field(default=None, min_length=3, max_length=120)
    marca: str | None = Field(default=None, min_length=2, max_length=120)
    cidade: str | None = Field(default=None, min_length=2, max_length=120)
    ativa: bool | None = None


class CasaResponse(CasaBase):
    """O que a API DEVOLVE. from_attributes lê direto do objeto SQLAlchemy."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    criado_em: datetime
    atualizado_em: datetime


class CasaPage(BaseModel):
    """Resposta paginada. Nunca devolva uma tabela inteira sem limite."""

    total: int
    limit: int
    offset: int
    items: list[CasaResponse]


# ------------------------------------------------------------ Upload de custo
class UploadCustoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    casa_id: int
    periodo: str
    nome_original: str
    blob_name: str
    content_type: str
    tamanho_bytes: int
    url: str
    criado_em: datetime
    itens_importados: int = Field(description="Quantas linhas de custo foram extraídas do arquivo")


class UploadCustoPage(BaseModel):
    """Resposta paginada. Nunca devolva uma tabela inteira sem limite."""

    total: int
    limit: int
    offset: int
    items: list[UploadCustoResponse]


# --------------------------------------------------------------- Item de custo
class ItemCustoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nome: str
    custo_teorico: float
    custo_real: float
    delta: float = Field(description="custo_real - custo_teorico")


# ------------------------------------------------------------------ Delta (RF02)
class DeltaCasaResponse(BaseModel):
    """Alimenta o painel de delta — RF02, prioridade nº1 do cliente."""

    casa_id: int
    casa_nome: str
    periodo: str
    custo_teorico_total: float
    custo_real_total: float
    delta_total: float = Field(description="custo_real_total - custo_teorico_total")
    itens: list[ItemCustoResponse] = Field(
        description="Itens ordenados pelo maior delta em módulo — onde está a maior perda"
    )


# ------------------------------------------------------------ Health/Erro
class HealthResponse(BaseModel):
    status: str
    versao: str
    ambiente: str
    banco: str


class ErroResponse(BaseModel):
    """Formato único de erro da API — o frontend trata um só formato."""

    detail: str
