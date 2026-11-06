"""Engine, Session e Base do SQLAlchemy.

Local  -> SQLite (arquivo projeto4.db)
Azure  -> Azure SQL Database, trocando apenas DATABASE_URL no .env / App Settings.
O código da aplicação não muda: é isso que o SQLAlchemy resolve.
"""

import logging
from collections.abc import Generator

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings

_is_sqlite = settings.database_url.startswith("sqlite")

engine = create_engine(
    settings.database_url,
    # check_same_thread é uma exigência exclusiva do SQLite
    connect_args={"check_same_thread": False} if _is_sqlite else {},
    # pool_pre_ping evita erro em conexão derrubada pelo Azure SQL por ociosidade
    pool_pre_ping=not _is_sqlite,
    echo=settings.debug,
)

logger = logging.getLogger(__name__)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    """Base declarativa de todos os models (tabelas)."""


def get_db() -> Generator[Session, None, None]:
    """Dependency injection da sessão do banco.

    Uso na rota:  def listar(db: Session = Depends(get_db)):
    A sessão é fechada automaticamente ao fim da requisição.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def criar_tabelas() -> None:
    """Cria as tabelas que ainda não existem.

    Serve para o laboratório e para os testes. A partir do momento em que o
    schema começar a evoluir, troque isto por migrations (Alembic).
    """
    _migrar_uploads_sem_tipo()
    try:
        Base.metadata.create_all(bind=engine)
    except DBAPIError as exc:
        # Com múltiplos workers do gunicorn, dois processos podem cair no
        # cold start ao mesmo tempo: o checkfirst do create_all não é atômico
        # entre processos, então o perdedor da corrida recebe "already
        # exists". O vencedor termina de criar o restante das tabelas sem
        # contenção, então é seguro ignorar aqui. O erro chega diferente em
        # cada banco: Azure SQL → ProgrammingError com SQLSTATE 42S01;
        # SQLite (usado no CI do container) → OperationalError "already exists".
        if not _tabela_ja_existe(exc):
            raise


def _tabela_ja_existe(exc: DBAPIError) -> bool:
    mensagem = str(exc.orig)
    return "42S01" in mensagem or "already exists" in mensagem


def _migrar_uploads_sem_tipo() -> None:
    """Migração única de 03/11/2026: `ItemCusto` (CSV fictício) → `LinhaCusto`.

    O `create_all` não altera tabela existente. Bancos criados antes desta data
    têm `uploads_custo` sem a coluna `tipo` e a tabela antiga `itens_custo`,
    que só guardavam dado de exemplo (CSV inventado). Elas são descartadas e
    recriadas no formato novo. Os blobs antigos ficam órfãos no storage.

    Quando o projeto adotar Alembic, isto vira a primeira migration.
    """
    try:
        inspetor = inspect(engine)
        if not inspetor.has_table("uploads_custo"):
            return
        colunas = {c["name"] for c in inspetor.get_columns("uploads_custo")}
        if "tipo" in colunas:
            return
        logger.warning("Migrando schema antigo: descartando itens_custo e uploads_custo")
        with engine.begin() as conexao:
            for tabela in ("itens_custo", "linhas_custo", "uploads_custo"):
                if inspetor.has_table(tabela):
                    conexao.execute(text(f"DROP TABLE {tabela}"))
    except DBAPIError:
        # Outro worker do gunicorn pode ter feito a migração ao mesmo tempo.
        logger.exception("Migração de uploads_custo falhou — provavelmente já feita")
