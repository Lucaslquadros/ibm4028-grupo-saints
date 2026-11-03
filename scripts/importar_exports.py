"""Importa exports reais do Everest direto no banco local (sem passar pela API).

    uv run python scripts/importar_exports.py \
        --casa "Boteco São Bento - Vila Madalena" \
        --tipo cardapio \
        --arquivo "dados_reais/SB VILA CMV CARDÁPIO.xlsx" \
        --periodos 2026-07 2026-08 2026-09

Usa os MESMOS tradutores da rota de upload (app/services/leitores.py), então o
que funciona aqui funciona no upload pela tela. Útil para popular o banco com
vários meses de uma vez (a planilha de CMV da equipe tem uma aba por mês).

Os arquivos reais ficam em dados_reais/, que está no .gitignore: eles têm CNPJ,
faturamento e custos do cliente e não podem ir para o GitHub.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select  # noqa: E402

from app import crud  # noqa: E402
from app.database import SessionLocal, criar_tabelas  # noqa: E402
from app.models import Casa  # noqa: E402
from app.services import storage  # noqa: E402
from app.services.leitores import LEITORES, ErroLeitura  # noqa: E402

XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--casa", required=True, help="Nome exato da casa (cria se não existir)")
    parser.add_argument("--tipo", required=True, choices=sorted(LEITORES))
    parser.add_argument("--arquivo", required=True, type=Path)
    parser.add_argument("--periodos", required=True, nargs="+", help="AAAA-MM, um ou mais")
    args = parser.parse_args()

    conteudo = args.arquivo.read_bytes()
    criar_tabelas()
    db = SessionLocal()
    try:
        casa = db.scalar(select(Casa).where(Casa.nome == args.casa))
        if casa is None:
            casa = Casa(nome=args.casa, marca=args.casa.split(" - ")[0], cidade="São Paulo")
            db.add(casa)
            db.commit()
            print(f"Casa criada: {casa.nome} (id {casa.id})")

        for periodo in args.periodos:
            try:
                extracao = LEITORES[args.tipo](conteudo, periodo)
            except ErroLeitura as exc:
                print(f"  {periodo}: ERRO — {exc}")
                continue
            blob_name, url = storage.salvar(conteudo, args.arquivo.name, XLSX)
            crud.registrar_upload_custo(
                db,
                casa_id=casa.id,
                periodo=periodo,
                tipo=args.tipo,
                nome_original=args.arquivo.name,
                blob_name=blob_name,
                content_type=XLSX,
                tamanho_bytes=len(conteudo),
                url=url,
                linhas=extracao.linhas,
            )
            fechamento = crud.calcular_fechamento(db, casa.id, periodo)
            total = fechamento["total"] if fechamento else {}
            print(
                f"  {periodo}: {len(extracao.linhas)} linhas | "
                f"CMV teórico {total.get('cmv_teorico_pct')}% | "
                f"CMV real {total.get('cmv_real_pct')}%"
            )
    finally:
        db.close()


if __name__ == "__main__":
    main()
