"""Engine, Session e Base do SQLAlchemy.

Local  -> SQLite (arquivo projeto4.db)
Azure  -> Azure SQL Database, trocando apenas DATABASE_URL no .env / App Settings.
O código da aplicação não muda: é isso que o SQLAlchemy resolve.
"""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.exc import ProgrammingError
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
    try:
        Base.metadata.create_all(bind=engine)
    except ProgrammingError as exc:
        # Com múltiplos workers do gunicorn, dois processos podem cair no
        # cold start ao mesmo tempo: o checkfirst do create_all não é atômico
        # entre processos, então o perdedor da corrida recebe "already
        # exists" (SQLSTATE 42S01) do Azure SQL. O vencedor termina de criar
        # o restante das tabelas sem contenção, então é seguro ignorar aqui.
        if "42S01" not in str(exc.orig):
            raise
