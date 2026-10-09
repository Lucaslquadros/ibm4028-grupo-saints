"""Dependências compartilhadas, no estilo `Annotated`.

Convenção da skill oficial do FastAPI: em vez de repetir
`db: Session = Depends(get_db)` em toda rota, cria-se um alias de tipo.

    def listar(db: DbSession): ...

Vantagens sobre o `= Depends()` no default:
  - a assinatura continua sendo uma assinatura Python válida e tipada;
  - o mesmo alias serve em rota, em outra dependência e em função comum;
  - nada de valor "mágico" como default de argumento.
"""

from typing import Annotated

from fastapi import Depends, Query
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.database import get_db

DbSession = Annotated[Session, Depends(get_db)]
"""Sessão do banco, aberta e fechada por requisição."""

AppSettings = Annotated[Settings, Depends(get_settings)]
"""Settings da aplicação. Injetadas (e não importadas direto) para poder
sobrescrever em teste via app.dependency_overrides."""


class Paginacao:
    """Parâmetros de paginação reaproveitados por qualquer listagem.

    Dependência de classe: agrupa parâmetros relacionados sem repetir
    `limit`/`offset` em cada assinatura.
    """

    def __init__(
        self,
        limit: Annotated[int, Query(ge=1, le=200, description="Itens por página")] = 50,
        offset: Annotated[int, Query(ge=0, description="Registros a pular")] = 0,
    ) -> None:
        self.limit = limit
        self.offset = offset


PaginacaoDep = Annotated[Paginacao, Depends(Paginacao)]
