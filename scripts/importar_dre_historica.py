"""Importa as DREs mensais coladas nas abas `ENTRADA - <mês>` da planilha de
fechamento da equipe (`RESULTADOS - SAO BENTO - VILA MADALENA.xls`) para o
banco local, como lado real em base **compras**.

    uv run --with xlrd python scripts/importar_dre_historica.py \
        --casa "Boteco São Bento - Vila Madalena" \
        --arquivo "dados_reais/RESULTADOS - SAO BENTO - VILA MADALENA.xls" \
        --periodos 2022-06 2022-07 2022-08 2022-09 2022-10 2022-11 2022-12

Por que existe: sem inventário, um mês isolado de compras × teórico não diz
nada (o estoque entra e sai). Somando meses, diz. A casa piloto só tem uma DRE
de 2026 (set/26); as abas ENTRADA trazem jun–dez/22, os mesmos meses que o
cardápio da equipe cobre. Importe o cardápio desses meses com
`importar_exports.py --tipo cardapio` e o fechamento ganha um acumulado de
7 meses.

O `.xls` (Excel 97) não é aceito pela API, que só recebe `.xlsx`. Aqui cada aba
é convertida em memória para um `.xlsx` de uma aba e passa pelo MESMO leitor
da rota (`leitores.ler("compras", ...)`, layout sem código de conta). O
período sai do título da coluna (`V. Jun/2022`), não do nome da aba, porque os
nomes das abas não seguem padrão (`ENTRADA - JUN 22`, `ENTRADA - AGO 2022`).

`xlrd` não é dependência do projeto: o `--with xlrd` do uv instala só para esta
execução. Arquivo real fica em `dados_reais/` (fora do Git).
"""

import argparse
import io
import re
import sys
from pathlib import Path

from openpyxl import Workbook

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select  # noqa: E402

from app import crud  # noqa: E402
from app.database import SessionLocal, criar_tabelas  # noqa: E402
from app.models import Casa  # noqa: E402
from app.services import leitores, storage  # noqa: E402
from app.services.leitores import XLSX, ErroLeitura  # noqa: E402

MESES = {
    "JAN": 1, "FEV": 2, "MAR": 3, "ABR": 4, "MAI": 5, "JUN": 6,
    "JUL": 7, "AGO": 8, "SET": 9, "OUT": 10, "NOV": 11, "DEZ": 12,
}  # fmt: skip
TITULO_VALOR = re.compile(r"V\.\s*([A-Za-z]{3})/(\d{4})")


def abas_por_periodo(caminho: Path) -> dict[str, list[list]]:
    """{'2022-06': linhas da aba} para cada aba ENTRADA com 'V. Mmm/AAAA'."""
    try:
        import xlrd
    except ImportError:
        sys.exit("Rode com: uv run --with xlrd python scripts/importar_dre_historica.py ...")

    livro = xlrd.open_workbook(str(caminho))
    resultado: dict[str, list[list]] = {}
    for aba in livro.sheets():
        if not aba.name.upper().startswith("ENTRADA") or aba.nrows == 0:
            continue
        cabecalho = [str(v) for v in aba.row_values(0)]
        achado = next((TITULO_VALOR.search(c) for c in cabecalho if TITULO_VALOR.search(c)), None)
        if achado is None:
            continue  # layout antigo, com 'Classificação' — fora do escopo
        mes = MESES.get(achado.group(1).upper())
        if mes is None:
            continue
        periodo = f"{achado.group(2)}-{mes:02d}"
        resultado[periodo] = [aba.row_values(i) for i in range(aba.nrows)]
    return resultado


def para_xlsx(linhas: list[list]) -> bytes:
    livro = Workbook()
    aba = livro.active
    for linha in linhas:
        aba.append([None if v == "" else v for v in linha])
    buffer = io.BytesIO()
    livro.save(buffer)
    return buffer.getvalue()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--casa", required=True, help="Nome exato da casa (cria se não existir)")
    parser.add_argument("--arquivo", required=True, type=Path)
    parser.add_argument("--periodos", nargs="*", help="AAAA-MM; sem isto, todos os achados")
    args = parser.parse_args()

    abas = abas_por_periodo(args.arquivo)
    periodos = args.periodos or sorted(abas)
    criar_tabelas()
    db = SessionLocal()
    try:
        casa = db.scalar(select(Casa).where(Casa.nome == args.casa))
        if casa is None:
            casa = Casa(nome=args.casa, marca=args.casa.split(" - ")[0], cidade="São Paulo")
            db.add(casa)
            db.commit()
            print(f"Casa criada: {casa.nome} (id {casa.id})")

        for periodo in periodos:
            if periodo not in abas:
                print(f"  {periodo}: nenhuma aba ENTRADA com 'V. ...' deste mês")
                continue
            conteudo = para_xlsx(abas[periodo])
            try:
                extracao = leitores.ler("compras", conteudo, periodo)
            except ErroLeitura as exc:
                print(f"  {periodo}: ERRO — {exc}")
                continue
            nome = f"DRE {periodo} (aba ENTRADA de {args.arquivo.name}).xlsx"
            blob_name, url = storage.salvar(conteudo, nome, XLSX)
            crud.registrar_upload_custo(
                db,
                casa_id=casa.id,
                periodo=periodo,
                tipo="compras",
                nome_original=nome,
                blob_name=blob_name,
                content_type=XLSX,
                tamanho_bytes=len(conteudo),
                url=url,
                linhas=extracao.linhas,
            )
            grupos = {g.nome: g.custo for g in extracao.por_nivel("grupo")}
            print(
                f"  {periodo}: ALIMENTOS {grupos.get('ALIMENTOS', 0):,.2f} | "
                f"BEBIDAS {grupos.get('BEBIDAS', 0):,.2f}"
            )
    finally:
        db.close()


if __name__ == "__main__":
    main()
