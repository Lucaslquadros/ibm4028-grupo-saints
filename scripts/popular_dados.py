"""Popula o banco com dados de exemplo, para o dashboard não nascer vazio.

    uv run python scripts/popular_dados.py          # insere
    uv run python scripts/popular_dados.py --limpar # apaga tudo antes

Dados de um subconjunto das casas do Grupo Saints, com um período de custo de
exemplo — para o time ter algo no banco antes do primeiro export real do
Everest chegar. Este script NÃO vai para produção: é ferramenta de
desenvolvimento.
"""

import sys
import uuid
from pathlib import Path

# `python scripts/popular_dados.py` coloca scripts/ no sys.path, não a raiz do
# projeto — sem esta linha o import de `app` falha com ModuleNotFoundError.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import SessionLocal, criar_tabelas  # noqa: E402
from app.models import Casa, ItemCusto, UploadCusto  # noqa: E402

PERIODO_EXEMPLO = "2026-09"

CASAS = [
    # (nome, marca, cidade)
    ("Boteco São Bento - Itaim", "Boteco São Bento", "São Paulo"),
    ("Tartuferia San Paolo - Morumbi", "Tartuferia San Paolo", "São Paulo"),
    ("Casa Yū - Itaim Bibi", "Casa Yū", "São Paulo"),
    ("Toca do Urso", "Toca do Urso", "Ribeirão Preto"),
    ("Beer Island Tap House - Vila Madalena", "Beer Island Tap House", "São Paulo"),
]

# (item, custo_teorico, custo_real) por casa — valores fictícios, só para demo
ITENS_CUSTO = [
    ("Grey Goose 750ml", 100.00, 120.00),
    ("Chopp Pilsen (barril)", 480.00, 460.00),
    ("Filé Mignon (kg)", 65.00, 70.00),
    ("Camarão VG (kg)", 90.00, 110.00),
]


def limpar(db) -> None:
    apagados = (
        db.query(ItemCusto).delete() + db.query(UploadCusto).delete() + db.query(Casa).delete()
    )
    db.commit()
    print(f"Removidos {apagados} registros.")


def popular(db) -> None:
    if db.query(Casa).count():
        print("O banco já tem casas. Use --limpar para recomeçar do zero.")
        return

    for nome, marca, cidade in CASAS:
        casa = Casa(nome=nome, marca=marca, cidade=cidade, ativa=True)
        db.add(casa)
        db.flush()  # garante casa.id antes de criar o upload

        upload = UploadCusto(
            casa_id=casa.id,
            periodo=PERIODO_EXEMPLO,
            nome_original="export-exemplo.csv",
            blob_name=f"{uuid.uuid4().hex}.csv",
            content_type="text/csv",
            tamanho_bytes=1024,
            url="file://seed-local",
        )
        upload.itens = [
            ItemCusto(nome=nome_item, custo_teorico=teorico, custo_real=real)
            for nome_item, teorico, real in ITENS_CUSTO
        ]
        db.add(upload)

    db.commit()

    total_casas = db.query(Casa).count()
    total_itens = db.query(ItemCusto).count()
    print(
        f"Inseridas {total_casas} casas e {total_itens} itens de custo (período {PERIODO_EXEMPLO})."
    )
    print("Agora abra:")
    print("  http://localhost:8000/docs")
    print(f"  http://localhost:8000/api/v1/metricas/delta?casa_id=1&periodo={PERIODO_EXEMPLO}")


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
