"""Schemas = contrato da API (Pydantic).

Declarar o tipo É escrever a validação — e a documentação junto.
Se o código dentro da função rodou, o dado já está válido. Não escreva `if`.
"""

from datetime import datetime
from typing import Literal

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
TipoUpload = Literal["cardapio", "compras"]


class UploadCustoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    casa_id: int
    periodo: str
    tipo: TipoUpload = Field(
        description="cardapio = engenharia de cardápio (CMV teórico); "
        "compras = DRE gerencial de compras (CMV real)"
    )
    nome_original: str
    blob_name: str
    content_type: str
    tamanho_bytes: int
    url: str
    criado_em: datetime
    linhas_importadas: int = Field(description="Quantas linhas foram extraídas do arquivo")
    substituiu_anterior: bool = Field(
        default=False,
        description="True quando já havia um upload da mesma casa/período/tipo e ele foi trocado",
    )


class UploadCustoPage(BaseModel):
    """Resposta paginada. Nunca devolva uma tabela inteira sem limite."""

    total: int
    limit: int
    offset: int
    items: list[UploadCustoResponse]


# ------------------------------------------------------- Fechamento de CMV
class LinhaFechamento(BaseModel):
    """Uma linha do fechamento: um grupo (ALIMENTOS, BEBIDAS) ou o TOTAL.

    Campos ficam `null` quando o relatório correspondente do mês ainda não foi
    enviado — ex.: só o cardápio subiu, então não há custo real ainda.
    """

    grupo: str
    venda_liquida: float | None = Field(description="Venda líquida do grupo (cardápio)")
    custo_teorico: float | None = Field(description="Vendas × ficha técnica (cardápio)")
    custo_real: float | None = Field(description="Custo de compras pós-inventário (DRE)")
    cmv_teorico_pct: float | None
    cmv_real_pct: float | None
    ajuste: float | None = Field(description="custo_real − custo_teorico, em R$")
    ajuste_pp: float | None = Field(description="cmv_real_pct − cmv_teorico_pct, em pontos")


class FechamentoResponse(BaseModel):
    """O painel de fechamento do mês — o relatório que hoje leva ~2 dias à mão."""

    casa_id: int
    casa_nome: str
    periodo: str
    tem_cardapio: bool
    tem_compras: bool
    total: LinhaFechamento
    grupos: list[LinhaFechamento]


class PontoEvolucao(BaseModel):
    periodo: str
    cmv_teorico_pct: float | None
    cmv_real_pct: float | None
    ajuste_pp: float | None


class ItemCardapioResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    nome: str
    grupo: str
    subgrupo: str | None
    quantidade: float | None
    venda_liquida: float | None
    custo: float
    cmv_pct: float | None = Field(description="custo ÷ venda líquida, em %")


# ------------------------------------------------- Previsão de demanda (RF07)
class PontoHistorico(BaseModel):
    periodo: str
    quantidade: float


class PrevisaoItem(BaseModel):
    """Demanda esperada de um item no próximo período.

    `sugestao_compra` é um **teto**, não uma ordem de compra: o sistema lê
    relatórios de venda e compra, nunca uma contagem, então não sabe o estoque
    atual. Quem compra subtrai o que já tem. Ver `app/services/previsao.py`.
    """

    nome: str
    grupo: str
    subgrupo: str | None
    meses_com_dado: int
    media_recente: float = Field(description="Média de venda dos últimos 3 meses com dado")
    tendencia_pct: float | None = Field(
        description="Variação entre as últimas 3 observações e as 3 anteriores, em %. "
        "null quando não há duas janelas completas"
    )
    indice_sazonal: float | None = Field(
        description="Quanto este mês do ano costuma fugir da média. 1,0 = sem efeito. "
        "null sem um ano de histórico"
    )
    demanda_prevista: float
    sugestao_compra: float = Field(description="Demanda prevista + margem, assumindo estoque zero")
    confianca: Literal["alta", "media", "baixa"]
    motivo_confianca: str = Field(description="Por que esta confiança — para a tela mostrar")
    historico: list[PontoHistorico]


class RecomendacaoCompraResponse(BaseModel):
    casa_id: int
    casa_nome: str
    periodo_base: str = Field(description="Último mês de histórico considerado")
    periodo_alvo: str = Field(description="Mês para o qual a demanda é prevista")
    margem_seguranca_pct: float
    metodo: str = Field(description="Como o número foi calculado, em uma frase")
    aviso: str = Field(description="Limite do cálculo, para ser exibido junto do número")
    alerta_dado: str | None = Field(
        default=None,
        description="Presente quando o próprio dado de entrada é suspeito — ex.: o mês-base "
        "com volume muito fora do padrão, indício de relatório incompleto",
    )
    itens: list[PrevisaoItem]


# ------------------------------------------------------------ Health/Erro
class HealthResponse(BaseModel):
    status: str
    versao: str
    ambiente: str
    banco: str


class ErroResponse(BaseModel):
    """Formato único de erro da API — o frontend trata um só formato."""

    detail: str
