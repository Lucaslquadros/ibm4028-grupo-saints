"""Popula o banco com dados de exemplo, para o dashboard não nascer vazio.

    uv run python scripts/popular_dados.py          # insere
    uv run python scripts/popular_dados.py --limpar # apaga tudo antes

Cria um subconjunto das casas do Grupo Saints. Os custos NÃO são mais
inventados aqui: para ter dado no dashboard, importe os exports reais do
Everest com `scripts/importar_exports.py` (ver docs/07-fechamento-cmv.md).
Este script NÃO vai para produção: é ferramenta de desenvolvimento.
"""

import sys
from pathlib import Path

# `python scripts/popular_dados.py` coloca scripts/ no sys.path, não a raiz do
# projeto — sem esta linha o import de `app` falha com ModuleNotFoundError.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import SessionLocal, criar_tabelas  # noqa: E402
from app.models import Casa, LinhaCusto, UploadCusto  # noqa: E402

CASAS = [
    # (nome, marca, cidade)
    ("Boteco São Bento - Vila Madalena", "Boteco São Bento", "São Paulo"),  # casa piloto
    ("Boteco São Bento - Itaim", "Boteco São Bento", "São Paulo"),
    ("Tartuferia San Paolo - Morumbi", "Tartuferia San Paolo", "São Paulo"),
    ("Casa Yū - Itaim Bibi", "Casa Yū", "São Paulo"),
    ("Toca do Urso", "Toca do Urso", "Ribeirão Preto"),
    ("Beer Island Tap House - Vila Madalena", "Beer Island Tap House", "São Paulo"),
]


def limpar(db) -> None:
    apagados = (
        db.query(LinhaCusto).delete() + db.query(UploadCusto).delete() + db.query(Casa).delete()
    )
    db.commit()
    print(f"Removidos {apagados} registros.")


def popular(db) -> None:
    if db.query(Casa).count():
        print("O banco já tem casas. Use --limpar para recomeçar do zero.")
        return

    for nome, marca, cidade in CASAS:
        db.add(Casa(nome=nome, marca=marca, cidade=cidade, ativa=True))
    db.commit()

    print(f"Inseridas {db.query(Casa).count()} casas.")
    print("Para ter dado no painel, importe os exports reais:")
    print("  uv run python scripts/importar_exports.py --help")


def main() -> None:
    criar_tabelas()
    db = SessionLocal()
    try:
        if "--limpar" in sys.argv:
            limpar(db)
        popular(db)
    finally:
        db.close()


if __name__ == "__main__":
    main()
