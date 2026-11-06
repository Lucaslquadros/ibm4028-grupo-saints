"""Compatibilidade das queries com o Azure SQL.

Por que este arquivo existe: a suíte roda em SQLite (rápido, sem container,
sem credencial), mas produção é Azure SQL. O SQLite é **mais permissivo**, e
toda query que depende dessa permissividade passa verde aqui e devolve 500 lá.

Foi o que aconteceu com `GET /api/v1/uploads-custo`: ficou 500 em produção
enquanto os 61 testes seguiam verdes. Em vez de só corrigir a query, os testes
abaixo checam a *classe* do erro, para a próxima não passar batido.
"""

from sqlalchemy import Column
from sqlalchemy.dialects import mssql

from app import crud
from app.models import LinhaCusto, UploadCusto


def _colunas_soltas_no_group_by(stmt) -> list[str]:
    """Colunas de tabela no SELECT que não são agregação nem estão no GROUP BY.

    É exatamente o que o SQL Server recusa com "column is invalid in the select
    list because it is not contained in either an aggregate function or the
    GROUP BY clause" — e o que o SQLite aceita calado.

    A checagem roda sobre o objeto `Select`, não sobre o texto do SQL, para não
    depender de formatação nem de maiúsculas.
    """
    agrupadas = {str(c) for c in stmt._group_by_clauses}
    if not agrupadas:  # sem GROUP BY não há o que violar
        return []
    return [
        str(coluna)
        for coluna in stmt.selected_columns
        # Só colunas reais de tabela importam: `func.count(...)` é agregação e
        # subquery escalar é um valor único — nenhuma das duas precisa agrupar.
        if isinstance(coluna, Column) and str(coluna) not in agrupadas
    ]


def test_listar_uploads_e_compativel_com_sql_server():
    stmt = crud.stmt_listar_uploads_custo(limit=50, offset=0, casa_id=1, periodo="2026-09")

    assert _colunas_soltas_no_group_by(stmt) == []
    # Compilar no dialeto real pega o que o SQLAlchemy não consegue renderizar
    # para o SQL Server. Paginar é o caso clássico: o SQL Server não tem LIMIT,
    # então exige ORDER BY (seja via OFFSET/FETCH, seja via ROW_NUMBER() — qual
    # dos dois o SQLAlchemy escolhe depende da versão do servidor, e um dialeto
    # construído sem conexão não sabe a versão; por isso não fixamos a forma).
    sql = str(stmt.compile(dialect=mssql.dialect())).upper()
    assert "ORDER BY" in sql


def test_nomes_mais_custosos_e_compativel_com_sql_server():
    """Esta query agrupa por `nome` e ordena por `SUM(custo)`. É válida no SQL
    Server porque só `nome` é selecionado — mas basta alguém adicionar uma
    coluna ao SELECT sem adicionar ao GROUP BY para repetir o 500 de produção."""
    stmt = crud.stmt_nomes_mais_custosos(casa_id=1, periodo="2026-09", limit=10)

    assert _colunas_soltas_no_group_by(stmt) == []
    sql = str(stmt.compile(dialect=mssql.dialect())).upper()
    assert "GROUP BY" in sql
    assert "ORDER BY" in sql  # obrigatório: o SQL Server não tem LIMIT


def test_a_checagem_pegaria_a_query_que_quebrou_em_producao():
    """Guarda do guarda: prova que `_colunas_soltas_no_group_by` acusa a forma
    antiga da query, em vez de aprovar qualquer coisa que receba."""
    from sqlalchemy import func, select

    quebrada = (
        select(UploadCusto, func.count(LinhaCusto.id))
        .outerjoin(LinhaCusto, LinhaCusto.upload_id == UploadCusto.id)
        .group_by(UploadCusto.id)  # só o id agrupado, mas o SELECT traz a tabela toda
    )

    soltas = _colunas_soltas_no_group_by(quebrada)

    assert "uploads_custo.casa_id" in soltas
    assert "uploads_custo.id" not in soltas  # essa estava no GROUP BY
