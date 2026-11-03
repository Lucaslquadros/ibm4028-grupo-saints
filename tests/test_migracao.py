"""Migração do schema antigo (ItemCusto) para o novo (LinhaCusto)."""

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.pool import StaticPool

import app.database as database


def test_banco_antigo_sem_coluna_tipo_e_recriado(monkeypatch):
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    with engine.begin() as conexao:
        conexao.execute(text("CREATE TABLE casas (id INTEGER PRIMARY KEY)"))
        conexao.execute(
            text("CREATE TABLE uploads_custo (id INTEGER PRIMARY KEY, casa_id INTEGER)")
        )
        conexao.execute(
            text("CREATE TABLE itens_custo (id INTEGER PRIMARY KEY, upload_id INTEGER)")
        )
    monkeypatch.setattr(database, "engine", engine)

    database._migrar_uploads_sem_tipo()

    inspetor = inspect(engine)
    assert not inspetor.has_table("itens_custo")
    assert not inspetor.has_table("uploads_custo")
    assert inspetor.has_table("casas")  # casas cadastradas são preservadas


def test_banco_ja_migrado_nao_e_alterado(monkeypatch):
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    database.Base.metadata.create_all(bind=engine)
    monkeypatch.setattr(database, "engine", engine)

    database._migrar_uploads_sem_tipo()

    assert inspect(engine).has_table("uploads_custo")
