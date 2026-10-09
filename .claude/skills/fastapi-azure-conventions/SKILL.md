---
name: fastapi-azure-conventions
description: Convenções de código do backend FastAPI deste projeto (IBM4028) - estrutura de pastas, separação schemas x models, estilo Annotated para dependências, status codes, paginação, conexão com Azure SQL e Blob Storage, configuração via pydantic-settings. Use ao criar ou revisar rota, router, schema Pydantic, model SQLAlchemy, função de CRUD, dependência, teste de API, ou ao conectar o projeto ao Azure SQL / Blob. Gatilhos - criar endpoint, novo recurso, APIRouter, Pydantic, SQLAlchemy, Depends, response_model, status code, CORS, paginação, DATABASE_URL, Azure SQL, Blob Storage, pyodbc, .env, pydantic-settings.
---

# Convenções FastAPI + Azure — IBM4028

Vale para todo código em `app/`. Fonte: Aula 04 + skill oficial `fastapi/fastapi`.

## Estrutura e responsabilidades

```
app/
├── main.py       Entrada, CORS, include_router, handler global de erro
├── config.py     Settings (pydantic-settings). Nenhum segredo no código
├── database.py   Engine, SessionLocal, Base, get_db
├── deps.py       Aliases Annotated: DbSession, AppSettings, PaginacaoDep
├── models.py     Tabelas (SQLAlchemy)      — como o dado é GUARDADO
├── schemas.py    Contratos (Pydantic)      — o que ENTRA e SAI da API
├── crud.py       Operações de banco        — rota não monta query
├── routers/      Endpoints por domínio
└── services/     Integrações externas (Blob Storage, e-mail…)
```

Regra: **rota fina**. A rota valida (via tipo), chama `crud`/`services` e escolhe o status code. Lógica de banco não mora em `routers/`.

## Schemas × Models — a confusão número um

| | `schemas.py` (Pydantic) | `models.py` (SQLAlchemy) |
|---|---|---|
| O que é | Contrato com o mundo | Tabela do banco |
| Muda quando | O contrato com o front muda | A modelagem do banco muda |
| Contém | `EventoCreate`, `EventoResponse` | `class Evento(Base)` |

Nunca devolva o model direto: vaza campo sensível (`email_dono`, `senha_hash`) e prende o banco ao formato da API.

Por recurso, escreva quatro schemas: `XBase`, `XCreate`, `XUpdate` (tudo opcional, para PATCH), `XResponse` (com `ConfigDict(from_attributes=True)`).

## Estilo `Annotated` — obrigatório

Nunca escreva `= Depends(...)` nem `= Query(...)` como valor default. Use aliases de tipo em `deps.py`:

```python
# app/deps.py
DbSession = Annotated[Session, Depends(get_db)]
AppSettings = Annotated[Settings, Depends(get_settings)]

# na rota
def listar_itens(db: DbSession, pag: PaginacaoDep) -> ItemPage: ...
```

Motivo: a assinatura continua sendo Python válido e tipado, o mesmo alias serve em rota e em outra dependência, e some o valor "mágico" no default.

**Não use `...` (Ellipsis).** Obrigatoriedade vem de *não haver default*:

```python
# ✘ nome: str = Field(..., min_length=3)
# ✔ nome: str = Field(min_length=3)
```

**Não use `RootModel`.** Devolva `list[ItemResponse]` direto.

## Router

Declare `prefix`, `tags` e `responses` no próprio `APIRouter`, não no `include_router()`:

```python
router = APIRouter(
    prefix="/api/v1/itens",
    tags=["itens"],
    responses={404: {"model": ErroResponse}},
)
```

Versione desde o primeiro dia (`/api/v1/`): permite evoluir sem quebrar cliente.

Anote o **tipo de retorno** da função (`-> ItemPage`). O FastAPI usa isso como `response_model` — não precisa dos dois.

## async × def

> Se dentro da função existe um `await`, use `async def`. Se não existe nenhum, `def` normal já resolve.

`def` normal é rodado numa threadpool e **não trava** o servidor. O erro clássico é o contrário: `async def` com chamada bloqueante dentro (`requests`, `time.sleep`, driver síncrono de banco) — isso segura a fila inteira da instância. No plano Free (F1) do App Service, isso derruba a aplicação para todo mundo.

Como este projeto usa SQLAlchemy síncrono, **as rotas de banco são `def` normal**. A rota de upload é `async def` porque tem `await arquivo.read()`.

## Status codes — o contrato

| Situação | Código |
|---|---|
| GET com sucesso | 200 |
| POST criou recurso | **201** |
| DELETE com sucesso | **204** (sem corpo) |
| Dado inválido / falha de validação | **422** |
| Recurso não existe | **404** |
| Sem autenticação / sem permissão | 401 / 403 |
| Tipo de arquivo não aceito | 415 |
| Arquivo grande demais | 413 |
| Bug no backend | 500 |

Nunca devolva 200 com `null` para "não achei" — obriga o front a adivinhar. Use `HTTPException`.

## Validação

Declarar o tipo **é** escrever a validação e a documentação. Se o código dentro da função rodou, o dado já está válido — não escreva `if` para checar tipo ou tamanho.

```python
nome: str = Field(min_length=3, max_length=120)
quantidade: int = Field(ge=0, le=1_000_000)
data: date                      # rejeita "12/09/2026", exige AAAA-MM-DD
item_id: int                    # /itens/abc vira 422 sozinho
```

## Paginação

Nenhuma listagem devolve tabela inteira. Sempre `limit`/`offset` com teto, e resposta `{total, limit, offset, items}`. Agregação (`SUM`, `COUNT`, `GROUP BY`) roda **no banco**, não em Python — trazer 500 mil linhas para somar derruba a instância.

## Configuração e segredos

Nenhum segredo no código. `pydantic-settings` lê de:

- **Local** → `.env` (está no `.gitignore`; versione só o `.env.example`)
- **Azure** → App Service › Configuration › Application Settings
- **Produção** → Azure Key Vault para o que é sensível

Nunca cole connection string, chave do Blob ou token do Azure em prompt de IA. Use placeholder.

## Azure SQL

Só muda a `DATABASE_URL`. O código não muda.

```
# local
sqlite:///./projeto4.db

# Azure SQL
mssql+pyodbc://USUARIO:SENHA@SERVIDOR.database.windows.net:1433/BANCO
  ?driver=ODBC+Driver+18+for+SQL+Server&Encrypt=yes&TrustServerCertificate=no
```

Exige o **ODBC Driver 18** instalado no SO e `pyodbc` (extra `azuresql` do `pyproject.toml`). Use `pool_pre_ping=True`: o Azure SQL derruba conexão ociosa e sem isso a primeira requisição depois da pausa falha.

No portal, libere o IP da máquina em **Networking › Firewall rules** e marque "Allow Azure services".

## Blob Storage

Binário no object storage, ponteiro no banco. Guardar arquivo em coluna de banco relacional é caro e não escala.

**Nunca reaproveite o nome enviado pelo cliente** como nome do blob: permite sobrescrever arquivo alheio e abre path traversal. Gere `uuid4().hex + extensão` e guarde o nome original apenas como metadado.

Valide tipo (415) e tamanho (413) **antes** de subir — upload rejeitado depois de enviado já custou banda e armazenamento.

## CORS

O erro de CORS vem do navegador, não do backend. Configure desde o início e **nunca use `["*"]` em produção** — liste o domínio real do frontend.

## Health check

`/health` é obrigatório. O App Service chama essa rota para decidir se reinicia a instância. Sem ela, uma aplicação travada continua recebendo tráfego e devolvendo erro. Cheque também o banco (`SELECT 1`) e nunca deixe o próprio health check estourar exceção.

## Erros de log

Stack trace vai para o log, **nunca** para a resposta HTTP — mensagem de erro detalhada em resposta é vazamento de informação. Use `logging` do Python; o Application Insights captura automaticamente.

## Testes

Um teste por comportamento do contrato: 201 ao criar, 404 ao não achar, 422 por validação, 204 ao apagar, POST não idempotente, GET idempotente, PATCH não apaga campo omitido.

Banco em memória por teste (`sqlite://` + `StaticPool`) e `app.dependency_overrides[get_db]` para injetar a sessão. É para isso que serve o `Depends()`.

## Checklist de PR

- [ ] Schema separado do model; `response_model` (ou tipo de retorno) declarado
- [ ] Dependências no estilo `Annotated`, sem `= Depends()` e sem `...`
- [ ] Status code correto (201/204/404/422), erro via `HTTPException`
- [ ] `async def` só onde há `await`
- [ ] Listagem paginada; agregação no banco
- [ ] Nenhum segredo no diff; `.env` fora do Git
- [ ] Teste cobrindo caminho feliz **e** o erro
- [ ] `uv run ruff check .` e `uv run pytest` passando
