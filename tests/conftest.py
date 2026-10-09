"""Fixtures dos testes.

Cada teste roda contra um banco SQLite novo, em memória. Teste que depende do
estado deixado pelo teste anterior é teste que passa sozinho e quebra na suíte.
"""

import os
from collections.abc import Generator

import pytest

# Precisa vir ANTES de importar app.config: as Settings leem o ambiente no import.
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["AZURE_STORAGE_CONNECTION_STRING"] = ""
os.environ["ENVIRONMENT"] = "test"

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import Session, sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.database import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    """Banco limpo por teste: cria o schema, entrega a sessão, derruba tudo.

    StaticPool + check_same_thread=False mantêm o MESMO banco em memória entre
    a thread do teste e a threadpool onde o FastAPI roda as rotas `def`.
    Sem isso, cada conexão veria um SQLite vazio diferente.
    """
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    fabrica = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    sessao = fabrica()
    try:
        yield sessao
    finally:
        sessao.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


@pytest.fixture
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """TestClient com a dependência get_db trocada pela sessão de teste.

    É para isto que serve o Depends(): trocar a implementação sem tocar na rota.
    """

    def _get_db_override() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = _get_db_override
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def client_sem_raise(db_session: Session) -> Generator[TestClient, None, None]:
    """Como `client`, mas sem o TestClient relançar a exceção original.

    Por padrão o TestClient propaga a exceção não tratada para o teste em vez
    de devolver a resposta 500 que `erro_nao_tratado` (app/main.py) gerou —
    isso mascararia justamente o comportamento que queremos testar.
    """

    def _get_db_override() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = _get_db_override
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def item_valido() -> dict:
    return {
        "nome": "Ração Premium 15kg",
        "descricao": "Ração seca para cães adultos",
        "categoria": "alimentacao",
        "quantidade": 10,
        "valor": 189.90,
    }
