"""Popula o banco com dados de exemplo, para o dashboard não nascer vazio.

    uv run python scripts/popular_dados.py          # insere
    uv run python scripts/popular_dados.py --limpar # apaga tudo antes

Os dados são de um pet shop — escolhidos só para dar realismo. Quando o domínio
real do projeto estiver definido, troque esta lista pelos dados do seu cliente.
Este script NÃO vai para produção: é ferramenta de desenvolvimento.
"""

import sys
from pathlib import Path

# `python scripts/popular_dados.py` coloca scripts/ no sys.path, não a raiz do
# projeto — sem esta linha o import de `app` falha com ModuleNotFoundError.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import SessionLocal, criar_tabelas  # noqa: E402
from app.models import Arquivo, Item  # noqa: E402

ITENS = [
    # (nome, categoria, quantidade, valor unitário)
    ("Ração Premium Cães Adultos 15kg", "alimentacao", 24, 189.90),
    ("Ração Filhotes 3kg", "alimentacao", 40, 74.50),
    ("Ração Gatos Castrados 10,1kg", "alimentacao", 18, 214.00),
    ("Petisco Bifinho Carne 500g", "alimentacao", 60, 19.90),
    ("Shampoo Neutro 700ml", "higiene", 35, 32.00),
    ("Tapete Higiênico 30un", "higiene", 52, 59.90),
    ("Escova Dentes Pet", "higiene", 27, 14.50),
    ("Coleira Antipulgas G", "saude", 15, 89.90),
    ("Vermífugo 4 comprimidos", "saude", 22, 46.00),
    ("Suplemento Articular 60cp", "saude", 9, 128.00),
    ("Brinquedo Corda Trançada", "acessorios", 44, 24.90),
    ("Comedouro Inox Duplo", "acessorios", 16, 79.90),
    ("Cama Retangular M", "acessorios", 7, 159.00),
    ("Arranhador Torre 60cm", "acessorios", 5, 219.00),
    ("Guia Retrátil 5m", "acessorios", 12, 67.50),
]


def limpar(db) -> None:
    apagados = db.query(Item).delete() + db.query(Arquivo).delete()
    db.commit()
    print(f"Removidos {apagados} registros.")


def popular(db) -> None:
    if db.query(Item).count():
        print("O banco já tem itens. Use --limpar para recomeçar do zero.")
        return

    db.add_all(
        Item(nome=nome, categoria=cat, quantidade=qtd, valor=valor)
        for nome, cat, qtd, valor in ITENS
    )
    db.commit()

    total = db.query(Item).count()
    print(f"Inseridos {total} itens em 4 categorias.")
    print("Agora abra:")
    print("  http://localhost:8000/docs")
    print("  http://localhost:8000/api/v1/metricas/resumo")


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
