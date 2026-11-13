"""Leitor da planilha-modelo de fechamento (12/11/2026).

Uma linha por grupo por mês, com tudo o que o CMV real precisa:

    periodo | grupo     | venda_liquida | custo_teorico | estoque_inicial | compras | estoque_final
    2026-08 | ALIMENTOS |       270.000 |        72.900 |                 |  78.000 |        44.000

    CMV real = estoque_inicial + compras − estoque_final
    estoque_inicial em branco = estoque_final do mesmo grupo no mês anterior

Diferente dos leitores do Everest (`leitores.py`), aqui o arquivo traz o
período e os dois lados juntos: um envio pode carregar um mês ou um ano
inteiro. O modelo que a API gera está em `modelo_fechamento.py`.

Este módulo só valida o que dá para validar **dentro do arquivo**. Se o
estoque de abertura de um mês existe em envio anterior é pergunta para o
banco, e fica em `crud.meses_sem_estoque_inicial`.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

from app.services.leitores import ErroLeitura, _abrir, _normalizar, _padronizar, _texto

ABA = "FECHAMENTO"
"""Nome da aba lida. Sem ela, vale a primeira aba do arquivo."""

COLUNAS = {
    "periodo": ("PERIODO", "MES", "COMPETENCIA"),
    "grupo": ("GRUPO", "CATEGORIA"),
    "venda_liquida": ("VENDA LIQUIDA", "VENDA", "RECEITA", "FATURAMENTO"),
    "custo_teorico": ("CUSTO TEORICO", "CMV TEORICO"),
    "estoque_inicial": ("ESTOQUE INICIAL", "EI"),
    "compras": ("COMPRAS",),
    "estoque_final": ("ESTOQUE FINAL", "EF"),
}
OBRIGATORIAS = ("periodo", "grupo", "venda_liquida", "compras", "estoque_final")
VALORES = ("venda_liquida", "custo_teorico", "estoque_inicial", "compras", "estoque_final")

MAX_ERROS = 10
"""Quantos erros a mensagem lista. Mais que isso é planilha no formato errado,
e a lista inteira só esconderia o primeiro, que é o que importa."""

_AAAA_MM = re.compile(r"^(\d{4})-(\d{1,2})$")
_MM_AAAA = re.compile(r"^(\d{1,2})/(\d{4})$")


@dataclass(frozen=True)
class MovimentoLido:
    periodo: str
    grupo: str
    venda_liquida: float
    compras: float
    estoque_final: float
    custo_teorico: float | None = None
    estoque_inicial: float | None = None


def ler_fechamento(conteudo: bytes) -> list[MovimentoLido]:
    """Planilha-modelo → movimentos validados, em ordem de (período, grupo).

    Levanta `ErroLeitura` com **todos** os problemas encontrados (até
    `MAX_ERROS`), cada um com o número da linha no Excel: corrigir um erro por
    envio, descobrindo o próximo só no envio seguinte, é o que faz o usuário
    desistir do arquivo.
    """
    livro = _abrir(conteudo)
    try:
        aba = next(
            (livro[nome] for nome in livro.sheetnames if _normalizar(nome) == ABA),
            livro[livro.sheetnames[0]],
        )
        linhas = [tuple(r) for r in aba.iter_rows(values_only=True)]
    finally:
        livro.close()

    cabecalho_idx, colunas = _achar_cabecalho(linhas)
    movimentos: list[MovimentoLido] = []
    erros: list[str] = []
    vistos: dict[tuple[str, str], int] = {}

    for idx, linha in enumerate(linhas[cabecalho_idx + 1 :], start=cabecalho_idx + 2):
        bruto_periodo = _celula(linha, colunas["periodo"])
        bruto_grupo = _texto(linha, colunas["grupo"])
        if _vazio(bruto_periodo) and not bruto_grupo:
            continue  # linha em branco

        problemas: list[str] = []
        periodo = _periodo(bruto_periodo)
        if periodo is None:
            problemas.append(
                f"período '{_mostrar(bruto_periodo)}' inválido (use AAAA-MM, ex.: 2026-09)"
            )
        if not bruto_grupo:
            problemas.append("falta o grupo")

        valores: dict[str, float | None] = {}
        for chave in VALORES:
            if chave not in colunas:
                valores[chave] = None
                continue
            bruto = _celula(linha, colunas[chave])
            valor = _valor(bruto)
            if valor is None and not _vazio(bruto):
                problemas.append(f"{chave} '{_mostrar(bruto)}' não é um número")
            elif valor is not None and valor < 0:
                problemas.append(f"{chave} negativo")
            elif valor is None and chave in OBRIGATORIAS:
                problemas.append(
                    "falta o estoque_final: sem inventário não há CMV real"
                    if chave == "estoque_final"
                    else f"falta {chave}"
                )
            valores[chave] = valor

        if not problemas:
            grupo = _padronizar(bruto_grupo)
            chave_mes = (periodo, grupo)
            if chave_mes in vistos:
                problemas.append(f"{grupo} em {periodo} repetido (já na linha {vistos[chave_mes]})")
            else:
                vistos[chave_mes] = idx
                movimentos.append(
                    MovimentoLido(
                        periodo=periodo,
                        grupo=grupo,
                        venda_liquida=valores["venda_liquida"],
                        custo_teorico=valores["custo_teorico"],
                        estoque_inicial=valores["estoque_inicial"],
                        compras=valores["compras"],
                        estoque_final=valores["estoque_final"],
                    )
                )

        erros.extend(f"Linha {idx}: {p}." for p in problemas)

    if erros:
        mostrados = erros[:MAX_ERROS]
        if len(erros) > MAX_ERROS:
            mostrados.append(f"… e mais {len(erros) - MAX_ERROS} problema(s).")
        raise ErroLeitura(" ".join(mostrados))
    if not movimentos:
        raise ErroLeitura("A planilha tem as colunas certas, mas nenhuma linha preenchida.")

    return sorted(movimentos, key=lambda m: (m.periodo, m.grupo))


def primeiros_meses_sem_estoque_inicial(
    movimentos: list[MovimentoLido],
) -> list[MovimentoLido]:
    """Os movimentos sem `estoque_inicial` cujo mês anterior **não** está no
    arquivo. São os únicos que dependem de um envio anterior para fechar."""
    no_arquivo = {(m.periodo, m.grupo) for m in movimentos}
    return [
        m
        for m in movimentos
        if m.estoque_inicial is None and (periodo_anterior(m.periodo), m.grupo) not in no_arquivo
    ]


def periodo_anterior(periodo: str) -> str:
    """'2026-01' → '2025-12'."""
    ano, mes = (int(x) for x in periodo.split("-"))
    return f"{ano - 1:04d}-12" if mes == 1 else f"{ano:04d}-{mes - 1:02d}"


# ----------------------------------------------------------------- utilidades
def _achar_cabecalho(linhas: list[tuple]) -> tuple[int, dict[str, int]]:
    for idx, linha in enumerate(linhas[:30]):
        titulos = {_normalizar(v): i for i, v in enumerate(linha) if v is not None}
        achadas = {
            chave: next((titulos[a] for a in aceitos if a in titulos), None)
            for chave, aceitos in COLUNAS.items()
        }
        if all(achadas[c] is not None for c in OBRIGATORIAS):
            return idx, {chave: i for chave, i in achadas.items() if i is not None}
    raise ErroLeitura(
        "Não reconheci este arquivo como a planilha de fechamento: a primeira linha precisa "
        "ter as colunas 'periodo', 'grupo', 'venda_liquida', 'compras' e 'estoque_final' "
        "('custo_teorico' e 'estoque_inicial' são opcionais). Baixe a planilha-modelo."
    )


def _celula(linha: tuple, idx: int) -> Any:
    return linha[idx] if idx < len(linha) else None


def _vazio(valor: Any) -> bool:
    return valor is None or (isinstance(valor, str) and not valor.strip())


def _mostrar(valor: Any) -> str:
    return str(valor).strip()[:30]


def _periodo(valor: Any) -> str | None:
    """'2026-09', '09/2026' ou uma data do Excel → '2026-09'. Senão, None.

    Data é aceita porque o Excel converte '2026-09' digitado numa célula sem
    formato de texto em 01/09/2026 — o usuário não fez nada de errado.
    """
    if isinstance(valor, datetime | date):
        return f"{valor.year:04d}-{valor.month:02d}"
    if not isinstance(valor, str):
        return None
    texto = valor.strip()
    if m := _AAAA_MM.match(texto):
        ano, mes = int(m.group(1)), int(m.group(2))
    elif m := _MM_AAAA.match(texto):
        mes, ano = int(m.group(1)), int(m.group(2))
    else:
        return None
    return f"{ano:04d}-{mes:02d}" if 1 <= mes <= 12 else None


def _valor(valor: Any) -> float | None:
    """Número da célula. Texto aceita '1.234,56' (com vírgula decimal) e
    '1234.56' (com ponto decimal). Diferente de `leitores._numero`, que trata
    todo ponto como separador de milhar e leria '1234.56' como 123456."""
    if _vazio(valor) or isinstance(valor, bool):
        return None
    if isinstance(valor, int | float):
        return float(valor)
    texto = str(valor).strip().replace("R$", "").replace(" ", "")
    if "," in texto:
        texto = texto.replace(".", "").replace(",", ".")
    try:
        return float(texto)
    except ValueError:
        return None
