"""Planilha-modelo `.xlsx` gerada na hora — P0 do ciclo 07/11 (docs/11, 4.2).

Por que um endpoint e não um arquivo versionado: a API aceita **só** `.xlsx`
(415 para o resto), os `exemplos/*.csv` só funcionam porque
`scripts/popular_demo_generico.py` converte antes de enviar, e o `.gitignore`
bloqueia `*.xlsx` de propósito — dado de cliente nunca entra no Git. Gerar o
modelo é mais barato do que abrir exceção na regra que protege o dado real.

O arquivo gerado é aceito de volta pelo próprio `POST /uploads-custo`: é o que
o teste `test_modelos.py` garante, para o modelo não descolar do leitor.
"""

import io
from typing import Annotated

from fastapi import APIRouter, HTTPException, Path, Query, Response
from openpyxl import Workbook

from app.schemas import DemoFechamento, ErroResponse, TipoUpload
from app.services import demo_fechamento
from app.services.leitores import XLSX
from app.services.modelo_fechamento import gerar_modelo_fechamento

router = APIRouter(prefix="/api/v1/modelos", tags=["modelos"])

TipoModelo = Annotated[
    TipoUpload,
    Path(
        description="cardapio = lado teórico (ficha técnica); compras = lado real (pós-inventário)"
    ),
]

AVISO = (
    "Modelo gerado pela API. Troque as linhas de exemplo pelos seus dados. "
    "O período é declarado no envio, não no arquivo."
)

# Cabeçalho e exemplo de cada lado, conforme a tabela C de
# `docs/07-fechamento-cmv.md`. Os números são sintéticos e redondos de
# propósito: nenhum valor da casa real pode sair daqui (regra 7 do ciclo).
#
# Os subgrupos são diferentes nos dois lados **de propósito** — é o limite real
# do dado que o RF11 declara: venda vem por categoria de cardápio (PETISCOS) e
# compra por categoria de insumo (BOVINOS). CHOPP e DESTILADOS existem nos dois
# e são os únicos que o sistema compara abaixo do grupo.
MODELOS: dict[str, dict] = {
    "cardapio": {
        "cabecalho": ["grupo", "subgrupo", "item", "quantidade", "venda_liquida", "custo"],
        "linhas": [
            ["ALIMENTOS", "PETISCOS", "BOLINHO DE BACALHAU", 120, 3600, 1260],
            ["ALIMENTOS", "PRATOS", "FILÉ COM FRITAS", 80, 5600, 2240],
            ["BEBIDAS", "CHOPP", "CHOPP 300ML", 900, 9000, 2700],
            ["BEBIDAS", "DESTILADOS", "CAIPIRINHA", 150, 3000, 900],
        ],
    },
    "compras": {
        "cabecalho": ["grupo", "subgrupo", "custo"],
        "linhas": [
            ["ALIMENTOS", "BOVINOS", 2100],
            ["ALIMENTOS", "HORTIFRUTI", 800],
            ["BEBIDAS", "CHOPP", 2600],
            ["BEBIDAS", "DESTILADOS", 950],
        ],
    },
}


def gerar_modelo(tipo: str) -> bytes:
    """Monta o `.xlsx` em memória. Função pura: nada de disco, nada de banco."""
    modelo = MODELOS[tipo]
    livro = Workbook()
    aba = livro.active
    aba.title = "Modelo"
    aba.append([AVISO])
    aba.append(modelo["cabecalho"])
    for linha in modelo["linhas"]:
        aba.append(linha)

    buffer = io.BytesIO()
    livro.save(buffer)
    return buffer.getvalue()


@router.get(
    "/fechamento/demo",
    summary="Casa de demonstração da planilha de fechamento: nome e meses",
)
def info_demo_fechamento() -> DemoFechamento:
    """Para a tela de Upload saber quando oferecer a planilha da demonstração:
    só para a casa de demonstração, nunca para uma casa real."""
    return DemoFechamento(
        casa_nome=demo_fechamento.CASA_DEMO["nome"],
        periodos=demo_fechamento.PERIODOS,
        periodos_historico=demo_fechamento.PERIODOS_HISTORICO,
        periodo_ao_vivo=demo_fechamento.PERIODO_AO_VIVO,
    )


@router.get(
    "/fechamento/demo/planilha",
    summary="Baixar a planilha preenchida da casa de demonstração",
    response_class=Response,
    responses={
        200: {"content": {XLSX: {}}, "description": "Planilha-modelo com os dados da demo"},
        422: {"model": ErroResponse},
    },
)
def baixar_planilha_demo(
    periodo: Annotated[
        list[str] | None,
        Query(description="Meses (AAAA-MM). Sem nenhum, vale o mês da apresentação ao vivo"),
    ] = None,
) -> Response:
    """Mesmo layout da planilha-modelo, com os números fictícios da casa de
    demonstração. Dados em `app/services/demo_fechamento.py`."""
    periodos = periodo or [demo_fechamento.PERIODO_AO_VIVO]
    desconhecidos = sorted(set(periodos) - set(demo_fechamento.PERIODOS))
    if desconhecidos:
        raise HTTPException(
            status_code=422,
            detail=f"A demonstração não tem os meses {', '.join(desconhecidos)}. "
            f"Disponíveis: {', '.join(demo_fechamento.PERIODOS)}.",
        )
    nome = f"demo-fechamento-{min(periodos)}" + (
        f"-a-{max(periodos)}" if len(set(periodos)) > 1 else ""
    )
    return Response(
        content=gerar_modelo_fechamento(demo_fechamento.linhas_demo(periodos)),
        media_type=XLSX,
        headers={"Content-Disposition": f'attachment; filename="{nome}.xlsx"'},
    )


# Declarada ANTES de `/{tipo}`: o FastAPI casa as rotas na ordem, e
# `/fechamento` cairia no `{tipo}` e tomaria 422 do `Literal`.
@router.get(
    "/fechamento",
    summary="Baixar planilha-modelo de fechamento (venda, teórico e estoque por grupo)",
    response_class=Response,
    responses={
        200: {
            "content": {XLSX: {}},
            "description": "Abas Fechamento (lida pelo sistema), Instrucoes e Conferencia",
        }
    },
)
def baixar_modelo_fechamento() -> Response:
    """Planilha de `POST /fechamentos`: uma linha por grupo por mês, com o
    movimento de estoque que o CMV real exige. Exemplo sintético de 3 meses."""
    return Response(
        content=gerar_modelo_fechamento(),
        media_type=XLSX,
        headers={"Content-Disposition": 'attachment; filename="modelo-fechamento.xlsx"'},
    )


@router.get(
    "/{tipo}",
    summary="Baixar planilha-modelo do lado teórico ou do lado real",
    response_class=Response,
    responses={
        200: {
            "content": {XLSX: {}},
            "description": "Planilha com o cabeçalho do contrato de entrada e 4 linhas de exemplo",
        },
        422: {"model": ErroResponse},
    },
)
def baixar_modelo(tipo: TipoModelo) -> Response:
    """Planilha-modelo do lado pedido, com linhas de exemplo sintéticas.

    Tipo fora de `cardapio`/`compras` vira 422 pela validação do `Literal` —
    não há `if` aqui para isso.
    """
    return Response(
        content=gerar_modelo(tipo),
        media_type=XLSX,
        headers={"Content-Disposition": f'attachment; filename="modelo-{tipo}.xlsx"'},
    )
