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
    custo_real: float | None = Field(
        description="Custo do lado real. Só é CMV real com base_real = consumo "
        "(EI + compras − EF); com base_real = compras é o total comprado no mês"
    )
    cmv_teorico_pct: float | None
    cmv_real_pct: float | None
    ajuste: float | None = Field(description="custo_real − custo_teorico, em R$")
    ajuste_pp: float | None = Field(description="cmv_real_pct − cmv_teorico_pct, em pontos")


# ------------------------------------------------- Explicação do ajuste (RF11)
class ContribuicaoGrupo(BaseModel):
    """Quanto cada grupo puxou o ajuste do mês, em pontos do TOTAL.

    Não confundir com o `ajuste_pp` de `LinhaFechamento`: lá o denominador é a
    venda do próprio grupo, e por isso aquele número **não soma** ao total.
    """

    grupo: str
    ajuste: float = Field(description="custo_real − custo_teorico do grupo, em R$")
    contribuicao_pp: float = Field(description="ajuste do grupo ÷ venda líquida total × 100")


class SubgrupoComparado(BaseModel):
    """Subgrupo presente nos DOIS lados do mês — o único caso em que a
    diferença abaixo do grupo é desvio, e não taxonomia diferente."""

    grupo: str
    subgrupo: str
    custo_teorico: float
    custo_real: float
    ajuste: float
    ajuste_pp: float | None = Field(
        description="ajuste ÷ venda do subgrupo no cardápio × 100; null sem venda"
    )


class SubgrupoSemPar(BaseModel):
    """Subgrupo que existe em um lado só. É **composição do custo**, nunca
    desvio: o ERP informa compra por categoria de insumo (BOVINOS) e venda por
    categoria de cardápio (PETISCOS)."""

    grupo: str
    subgrupo: str
    lado: Literal["teorico", "real"]
    custo: float


class Explicacao(BaseModel):
    """Onde o ajuste do mês está e o que conferir — RF11.

    Gerada por regras em `app/services/explicacao.py`, sem LLM, para o sócio
    (Persona 2). `situacao` tem três valores porque ajuste negativo **não é
    economia**: é divergência na direção oposta.
    """

    situacao: Literal["acima", "dentro", "abaixo"]
    limiar_pp: float = Field(
        description="Margem considerada normal, em pontos. É premissa nossa, não "
        "do cliente — por isso volta na resposta, para a tela exibir junto"
    )
    resumo: str = Field(description="O parágrafo que a tela mostra acima do número")
    sugestoes: list[str] = Field(description="No máximo 2. Vazia quando está dentro da margem")
    contribuicoes: list[ContribuicaoGrupo]
    grupos_sem_par: list[str] = Field(
        description="Grupos com só um dos dois lados no mês: distorcem o total, "
        "e por isso são declarados em vez de escondidos"
    )
    subgrupos_comparados: list[SubgrupoComparado]
    subgrupos_sem_par: list[SubgrupoSemPar]
    limite_dado: str = Field(description="Por que a comparação por subgrupo pode vir quase vazia")
    conclusivo: bool = Field(
        default=True,
        description="false quando o lado real é só compras (sem estoque): aí "
        "`situacao` descreve compras × teórico e não serve de diagnóstico do mês",
    )


BaseReal = Literal["consumo", "compras", "declarada"]
"""Em que base está o lado real.

- consumo:   estoque inicial + compras − estoque final — o CMV real
- compras:   só as compras do mês (DRE do Everest); falta a variação de estoque
- declarada: planilha genérica com uma coluna `custo`; o usuário declara que é o real
"""


class Acumulado(BaseModel):
    """Teórico × real somados nos meses com os dois lados (janela de 12 meses).

    Com o lado real em compras, é a única leitura que faz sentido: mês a mês a
    diferença mistura desvio com ritmo de compra e estoque; somando meses, a
    variação de estoque se dilui.
    """

    periodo_inicio: str
    periodo_fim: str
    meses: int
    periodos: list[str]
    base_real: BaseReal
    conclusivo: bool = Field(
        description="Com base compras, só a partir de `meses_minimos` meses somados"
    )
    meses_minimos: int
    ajuste_mensal_min_pp: float | None = Field(
        description="Menor ajuste de um mês isolado na janela: mostra o tamanho do ruído"
    )
    ajuste_mensal_max_pp: float | None
    total: LinhaFechamento
    grupos: list[LinhaFechamento]


class FechamentoResponse(BaseModel):
    """O painel de fechamento do mês — o relatório que hoje leva ~2 dias à mão."""

    casa_id: int
    casa_nome: str
    periodo: str
    tem_cardapio: bool
    tem_compras: bool
    total: LinhaFechamento
    grupos: list[LinhaFechamento]
    explicacao: Explicacao | None = Field(
        default=None,
        description="RF11. null quando falta um dos dois lados do mês — nunca "
        "gerar texto sobre ajuste que não existe. Campo OPCIONAL de propósito: "
        "o frontend em produção continua funcionando entre o deploy do backend "
        "e o do front",
    )
    base_real: BaseReal | None = Field(
        default=None, description="Base do lado real no mês. null sem lado real"
    )
    acumulado: Acumulado | None = Field(
        default=None,
        description="Somas dos meses com os dois lados até este período. null quando "
        "nenhum mês da janela tem os dois relatórios",
    )


class PontoEvolucao(BaseModel):
    periodo: str
    cmv_teorico_pct: float | None
    cmv_real_pct: float | None
    ajuste_pp: float | None
    base_real: BaseReal | None = None


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
    commit: str = Field(
        description="SHA do commit publicado, ou 'desconhecido' fora do deploy "
        "automatizado. É o que o workflow compara para saber se o código que "
        "está rodando é o que acabou de ser publicado"
    )


class ErroResponse(BaseModel):
    """Formato único de erro da API — o frontend trata um só formato."""

    detail: str
