"""Tradutores dos exports do Everest para o formato único de `LinhaCusto`.

Os relatórios do Everest são "relatórios de impressão" exportados para Excel,
não tabelas de dados: têm cabeçalho de empresa, totais misturados com itens e
hierarquia por posição/código. Cada tradutor entende um layout e devolve a
mesma estrutura — é isso que deixa o resto do sistema ignorar o formato de
origem.

    cardápio (engenharia de cardápio) → CMV teórico
    compras  (DRE gerencial)          → CMV real

Qualquer formato inesperado vira `ErroLeitura`, que a rota transforma em 422
com uma mensagem que o usuário consegue entender. Dado que vem de fora nunca é
confiável.
"""

from __future__ import annotations

import io
import re
import unicodedata
import zipfile
from dataclasses import dataclass, field
from typing import Any

from openpyxl import load_workbook

MESES = (
    "JANEIRO",
    "FEVEREIRO",
    "MARCO",
    "ABRIL",
    "MAIO",
    "JUNHO",
    "JULHO",
    "AGOSTO",
    "SETEMBRO",
    "OUTUBRO",
    "NOVEMBRO",
    "DEZEMBRO",
)

CODIGO_CONTA = re.compile(r"^\d+(\.\d+)*$")


class ErroLeitura(ValueError):  # noqa: N818 - nome em português, como o resto do domínio
    """O arquivo não está no formato esperado. Mensagem pensada para o usuário."""


@dataclass
class Linha:
    nivel: str  # "total" | "grupo" | "subgrupo" | "item"
    grupo: str
    nome: str
    custo: float
    subgrupo: str | None = None
    quantidade: float | None = None
    venda_liquida: float | None = None


@dataclass
class Extracao:
    linhas: list[Linha] = field(default_factory=list)

    def por_nivel(self, nivel: str) -> list[Linha]:
        return [linha for linha in self.linhas if linha.nivel == nivel]


# ----------------------------------------------------------------- utilidades
def _normalizar(texto: Any) -> str:
    """'Custo Unitário ' → 'CUSTO UNITARIO'. Remove acento, pontuação e espaço extra."""
    if texto is None:
        return ""
    sem_acento = unicodedata.normalize("NFKD", str(texto)).encode("ascii", "ignore").decode()
    return " ".join(re.sub(r"[^A-Z0-9 ]", " ", sem_acento.upper()).split())


def _numero(valor: Any) -> float | None:
    """Aceita número ou texto no formato brasileiro ('1.234,56')."""
    if valor is None or valor == "":
        return None
    if isinstance(valor, bool):
        return None
    if isinstance(valor, int | float):
        return float(valor)
    texto = str(valor).strip().replace(".", "").replace(",", ".")
    try:
        return float(texto)
    except ValueError:
        return None


def _abrir(conteudo: bytes):
    try:
        return load_workbook(io.BytesIO(conteudo), read_only=True, data_only=True)
    except (zipfile.BadZipFile, KeyError, OSError, ValueError) as exc:
        raise ErroLeitura(
            "Não consegui abrir o arquivo como planilha .xlsx. "
            "Exporte do Everest em Excel (.xlsx) e envie de novo."
        ) from exc


def nome_aba_do_periodo(periodo: str) -> str:
    """'2026-09' → 'SETEMBRO26' (o padrão de nome das abas da planilha de CMV)."""
    ano, mes = periodo.split("-")
    return f"{MESES[int(mes) - 1]}{ano[2:]}"


def _escolher_aba(livro, periodo: str):
    """Export cru do Everest tem uma aba só. A planilha de acompanhamento da
    equipe tem uma aba por mês ('SETEMBRO26 25,17') — escolhemos a do período.
    """
    if len(livro.sheetnames) == 1:
        return livro[livro.sheetnames[0]]

    alvo = nome_aba_do_periodo(periodo)
    for nome in livro.sheetnames:
        if _normalizar(nome).replace(" ", "").startswith(alvo):
            return livro[nome]

    raise ErroLeitura(
        f"A planilha tem {len(livro.sheetnames)} abas e nenhuma corresponde ao período "
        f"{periodo} (procurei uma aba começando com '{alvo}')."
    )


# ------------------------------------------------------- cardápio → teórico
COLUNAS_CARDAPIO = {
    "quantidade": "Q VENDA",
    "venda_liquida": "V VENDA LIQUIDA",
    "custo": "CUSTO GERAL",
}


def ler_cardapio(conteudo: bytes, periodo: str) -> Extracao:
    """Engenharia de cardápio do Everest → CMV teórico.

    Layout (uma aba):
      linha de títulos com 'Q. Venda', 'V. Venda Líquida', 'Custo Geral'
      coluna A preenchida = grupo (se a próxima linha também tem coluna A) ou subgrupo
      coluna A vazia + coluna B preenchida = item
      'RESULTADO FINAL' = total do relatório, na linha seguinte
    """
    livro = _abrir(conteudo)
    try:
        linhas = [tuple(r) for r in _escolher_aba(livro, periodo).iter_rows(values_only=True)]
    finally:
        livro.close()

    cabecalho_idx, colunas = _achar_cabecalho_cardapio(linhas)
    extracao = Extracao()
    grupo: str | None = None
    subgrupo: str | None = None

    corpo = linhas[cabecalho_idx + 1 :]
    for i, linha in enumerate(corpo):
        col_a = _texto(linha, 0)
        col_b = _texto(linha, 1)

        if col_b and _normalizar(col_b).startswith("RESULTADO FINAL"):
            total = _linha_total_cardapio(corpo[i:], colunas)
            if total:
                extracao.linhas.append(total)
            break
        if col_b and _normalizar(col_b).startswith("TOTAL GERAL"):
            continue  # bloco de eventos: já entra no RESULTADO FINAL

        valores = {
            chave: _numero(linha[idx]) if idx < len(linha) else None
            for chave, idx in colunas.items()
        }

        if col_a:
            proxima_a = _texto(corpo[i + 1], 0) if i + 1 < len(corpo) else None
            if proxima_a:
                grupo, subgrupo, nivel = col_a, None, "grupo"
            else:
                subgrupo, nivel = col_a, "subgrupo"
            if grupo is None:
                raise ErroLeitura(f"Subgrupo '{col_a}' aparece antes de qualquer grupo.")
            extracao.linhas.append(
                Linha(
                    nivel=nivel,
                    grupo=grupo,
                    subgrupo=subgrupo,
                    nome=col_a,
                    custo=valores["custo"] or 0.0,
                    quantidade=valores["quantidade"],
                    venda_liquida=valores["venda_liquida"],
                )
            )
        elif col_b and valores["quantidade"] is not None and grupo:
            extracao.linhas.append(
                Linha(
                    nivel="item",
                    grupo=grupo,
                    subgrupo=subgrupo,
                    nome=col_b,
                    custo=valores["custo"] or 0.0,
                    quantidade=valores["quantidade"],
                    venda_liquida=valores["venda_liquida"],
                )
            )

    if not extracao.por_nivel("grupo"):
        raise ErroLeitura(
            "Não encontrei nenhum grupo (ALIMENTOS, BEBIDAS…) no relatório de cardápio."
        )
    return extracao


def _texto(linha: tuple, idx: int) -> str | None:
    if idx >= len(linha) or linha[idx] is None:
        return None
    texto = str(linha[idx]).strip()
    return texto or None


def _achar_cabecalho_cardapio(linhas: list[tuple]) -> tuple[int, dict[str, int]]:
    for idx, linha in enumerate(linhas[:30]):
        titulos = {_normalizar(v): i for i, v in enumerate(linha) if v is not None}
        if all(t in titulos for t in COLUNAS_CARDAPIO.values()):
            return idx, {chave: titulos[t] for chave, t in COLUNAS_CARDAPIO.items()}
    raise ErroLeitura(
        "Não reconheci este arquivo como engenharia de cardápio: faltam as colunas "
        "'Q. Venda', 'V. Venda Líquida' e 'Custo Geral'."
    )


def _linha_total_cardapio(bloco: list[tuple], colunas: dict[str, int]) -> Linha | None:
    """O RESULTADO FINAL tem títulos próprios na mesma linha e os valores na seguinte."""
    if len(bloco) < 2:
        return None
    titulos = {_normalizar(v): i for i, v in enumerate(bloco[0]) if v is not None}
    valores = bloco[1]
    venda_idx = titulos.get(COLUNAS_CARDAPIO["venda_liquida"])
    custo_idx = titulos.get(COLUNAS_CARDAPIO["custo"])
    if venda_idx is None or custo_idx is None:
        return None
    custo = _numero(valores[custo_idx])
    if custo is None:
        return None
    return Linha(
        nivel="total",
        grupo="TOTAL",
        nome="RESULTADO FINAL",
        custo=custo,
        venda_liquida=_numero(valores[venda_idx]),
    )


# ---------------------------------------------------------- compras → real
def ler_compras(conteudo: bytes, periodo: str) -> Extracao:
    """DRE gerencial do Everest → CMV real (de compras, pós-inventário).

    Layout: cada linha tem um código de conta e a descrição indentada.
      '(=) RECEITA LIQUIDA'  sem código  → receita do mês
      '2.01'      CUSTOS                 → total de custos
      '2.01.01'   ALIMENTOS              → grupo   (3 níveis)
      '2.01.01.00002' BOVINOS            → subgrupo (4 níveis)
    """
    livro = _abrir(conteudo)
    try:
        linhas = [tuple(r) for r in _escolher_aba(livro, periodo).iter_rows(values_only=True)]
    finally:
        livro.close()

    extracao = Extracao()
    receita: float | None = None
    custo_total: float | None = None
    grupo: str | None = None

    for linha in linhas:
        codigo, descricao, valor = _decompor_linha_dre(linha)
        if descricao is None or valor is None:
            continue

        if codigo is None:
            if "RECEITA LIQUIDA" in _normalizar(descricao):
                receita = valor
            continue

        niveis = codigo.split(".")
        if len(niveis) == 2 and _normalizar(descricao) == "CUSTOS":
            custo_total = valor
        elif len(niveis) == 3:
            grupo = descricao
            extracao.linhas.append(Linha(nivel="grupo", grupo=grupo, nome=descricao, custo=valor))
        elif len(niveis) == 4 and grupo:
            extracao.linhas.append(
                Linha(
                    nivel="subgrupo", grupo=grupo, subgrupo=descricao, nome=descricao, custo=valor
                )
            )

    if not extracao.por_nivel("grupo"):
        raise ErroLeitura(
            "Não reconheci este arquivo como DRE de compras: não encontrei contas de custo "
            "com código (ex.: '2.01.01 ALIMENTOS')."
        )

    if custo_total is None:
        custo_total = sum(linha.custo for linha in extracao.por_nivel("grupo"))
    extracao.linhas.insert(
        0,
        Linha(
            nivel="total",
            grupo="TOTAL",
            nome="RECEITA LIQUIDA / CUSTOS",
            custo=custo_total,
            venda_liquida=receita,
        ),
    )
    return extracao


def _decompor_linha_dre(linha: tuple) -> tuple[str | None, str | None, float | None]:
    """(código, descrição, valor). Procura por posição relativa, não absoluta:
    o export às vezes desloca colunas."""
    codigo = descricao = None
    valor = None
    for celula in linha:
        if celula is None:
            continue
        if descricao is None:
            texto = str(celula).strip()
            if codigo is None and CODIGO_CONTA.match(texto):
                codigo = texto
                continue
            if isinstance(celula, str) and texto:
                descricao = texto
            continue
        valor = _numero(celula)
        break
    return codigo, descricao, valor


# ------------------------------------------- planilha genérica (qualquer ERP)
# Nomes aceitos para cada coluna. A planilha é localizada por nome de coluna,
# nunca por posição: a ordem das colunas não importa e sobram colunas extras.
COLUNAS_PLANILHA = {
    "grupo": ("GRUPO", "CATEGORIA"),
    "subgrupo": ("SUBGRUPO", "SUBCATEGORIA"),
    "item": ("ITEM", "PRODUTO", "DESCRICAO"),
    "quantidade": ("QUANTIDADE", "QTD", "Q VENDA"),
    "venda_liquida": ("VENDA LIQUIDA", "VENDA", "RECEITA", "FATURAMENTO"),
    "custo": ("CUSTO", "CUSTO TOTAL"),
}
OBRIGATORIAS_PLANILHA = ("grupo", "custo")


def ler_planilha(conteudo: bytes, periodo: str) -> Extracao:
    """Planilha tabular genérica → qualquer lado do fechamento.

    Existe para sustentar a afirmação de que o sistema não está preso ao
    Everest. `ler_cardapio` e `ler_compras` decodificam dois relatórios de
    impressão específicos; este lê uma **tabela comum**, que qualquer ERP
    consegue exportar (ou que o usuário monta à mão):

        grupo      | subgrupo | item        | quantidade | venda_liquida | custo
        ALIMENTOS  | PETISCOS | BOLINHO     |         10 |        600.00 | 200.00
        BEBIDAS    | CHOPP    | CHOPP 300ML |        100 |       2000.00 | 400.00

    Só `grupo` e `custo` são obrigatórios — um relatório de compras não tem
    venda, e um relatório sem detalhe de item traz só o nível de grupo.

    A hierarquia é **calculada**, não lida: o arquivo traz as linhas planas e
    aqui somamos subgrupo, grupo e total. É o que permite a mesma planilha
    alimentar o fechamento sem o usuário ter que replicar os totais do Everest.

    Este leitor é agnóstico ao lado do fechamento: quem diz se é teórico ou
    real é o campo `tipo` do upload, não o formato do arquivo.
    """
    livro = _abrir(conteudo)
    try:
        linhas = [tuple(r) for r in _escolher_aba(livro, periodo).iter_rows(values_only=True)]
    finally:
        livro.close()

    cabecalho_idx, colunas = _achar_cabecalho_planilha(linhas)

    # Somas acumuladas: a planilha é plana, a hierarquia nasce daqui.
    por_grupo: dict[str, list[float | None]] = {}
    por_subgrupo: dict[tuple[str, str], list[float | None]] = {}
    itens: list[Linha] = []

    for linha in linhas[cabecalho_idx + 1 :]:
        grupo = _celula_texto(linha, colunas.get("grupo"))
        custo = _celula_numero(linha, colunas.get("custo"))
        if not grupo or custo is None:
            continue  # linha em branco ou rodapé

        subgrupo = _celula_texto(linha, colunas.get("subgrupo"))
        item = _celula_texto(linha, colunas.get("item"))
        quantidade = _celula_numero(linha, colunas.get("quantidade"))
        venda = _celula_numero(linha, colunas.get("venda_liquida"))

        _acumular(por_grupo, grupo, custo, venda)
        if subgrupo:
            _acumular(por_subgrupo, (grupo, subgrupo), custo, venda)
        if item:
            itens.append(
                Linha(
                    nivel="item",
                    grupo=grupo,
                    subgrupo=subgrupo,
                    nome=item,
                    custo=custo,
                    quantidade=quantidade,
                    venda_liquida=venda,
                )
            )

    if not por_grupo:
        raise ErroLeitura(
            "A planilha tem as colunas certas, mas nenhuma linha com grupo e custo preenchidos."
        )

    extracao = Extracao()
    custo_total = sum(soma[0] or 0.0 for soma in por_grupo.values())
    vendas = [soma[1] for soma in por_grupo.values() if soma[1] is not None]
    extracao.linhas.append(
        Linha(
            nivel="total",
            grupo="TOTAL",
            nome="TOTAL",
            custo=custo_total,
            venda_liquida=sum(vendas) if vendas else None,
        )
    )
    for grupo, (custo, venda) in por_grupo.items():
        extracao.linhas.append(
            Linha(nivel="grupo", grupo=grupo, nome=grupo, custo=custo or 0.0, venda_liquida=venda)
        )
    for (grupo, subgrupo), (custo, venda) in por_subgrupo.items():
        extracao.linhas.append(
            Linha(
                nivel="subgrupo",
                grupo=grupo,
                subgrupo=subgrupo,
                nome=subgrupo,
                custo=custo or 0.0,
                venda_liquida=venda,
            )
        )
    extracao.linhas.extend(itens)
    return extracao


def _acumular(destino: dict, chave, custo: float, venda: float | None) -> None:
    soma = destino.setdefault(chave, [0.0, None])
    soma[0] = (soma[0] or 0.0) + custo
    if venda is not None:
        soma[1] = (soma[1] or 0.0) + venda


def _celula_texto(linha: tuple, idx: int | None) -> str | None:
    return None if idx is None else _texto(linha, idx)


def _celula_numero(linha: tuple, idx: int | None) -> float | None:
    if idx is None or idx >= len(linha):
        return None
    return _numero(linha[idx])


def _achar_cabecalho_planilha(linhas: list[tuple]) -> tuple[int, dict[str, int]]:
    for idx, linha in enumerate(linhas[:30]):
        titulos = {_normalizar(v): i for i, v in enumerate(linha) if v is not None}
        achadas = {
            chave: next((titulos[a] for a in aceitos if a in titulos), None)
            for chave, aceitos in COLUNAS_PLANILHA.items()
        }
        if all(achadas[c] is not None for c in OBRIGATORIAS_PLANILHA):
            return idx, {chave: i for chave, i in achadas.items() if i is not None}
    raise ErroLeitura(
        "Não reconheci este arquivo como planilha genérica: a primeira linha precisa "
        "ter ao menos as colunas 'grupo' e 'custo'."
    )


# -------------------------------------------------------------- despacho
# Para cada lado do fechamento, os formatos aceitos **em ordem de tentativa**.
# O leitor específico do Everest vem primeiro; a planilha genérica é o fallback.
# Assim o usuário não precisa declarar o formato do arquivo — só dizer se o que
# ele está enviando é o lado teórico (cardapio) ou o real (compras).
LEITORES: dict[str, tuple] = {
    "cardapio": (ler_cardapio, ler_planilha),
    "compras": (ler_compras, ler_planilha),
}


def ler(tipo: str, conteudo: bytes, periodo: str) -> Extracao:
    """Traduz o arquivo tentando cada formato conhecido para aquele lado.

    Se nenhum reconhece, a mensagem do leitor **específico** é a que vai para o
    usuário: ela diz qual relatório do Everest era esperado, que é a informação
    útil em 99% dos casos. A da planilha genérica entra como alternativa.
    """
    erro_especifico: ErroLeitura | None = None
    for leitor in LEITORES[tipo]:
        try:
            return leitor(conteudo, periodo)
        except ErroLeitura as exc:
            if erro_especifico is None:
                erro_especifico = exc
    raise ErroLeitura(
        f"{erro_especifico} Como alternativa, envie uma planilha com as colunas 'grupo' e 'custo'."
    )
