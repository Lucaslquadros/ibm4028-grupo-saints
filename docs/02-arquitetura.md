# Arquitetura

**IBM4028 — Projeto 4 | IBMEC CDIA 2026.2**

## Visão geral

```
┌──────────────────┐        ┌───────────────────────┐        ┌────────────────────┐
│    Frontend      │        │  Backend (FastAPI)    │        │  Dados e Storage   │
│  Azure Static    │ HTTP   │  Azure App Service    │ HTTP   │  Azure SQL         │
│  Web App (React) │ JSON   │                       │ TDS    │  Blob Storage      │
│ • interface      ├───────►│ • rotas / endpoints   ├───────►│                    │
│ • consome a API  │        │ • validação (Pydantic)│        │ • banco relacional │
│ • dashboard      │◄───────┤ • regras de negócio   │◄───────┤ • arquivos         │
└──────────────────┘        │ • autenticação        │        └────────────────────┘
                            └───────────┬───────────┘
                                        │ telemetria
                                        ▼
                            ┌───────────────────────┐
                            │ Application Insights  │
                            │ logs • métricas •     │
                            │ tracing • alertas     │
                            └───────────────────────┘
```

Deploy do backend e do Static Web App: `docs/06-guia-deploy-azure.md`.

## Camadas do backend

| Arquivo | Responsabilidade |
|---|---|
| `app/main.py` | Entrada, CORS, `include_router`, handler global de erro |
| `app/config.py` | Settings via `pydantic-settings` — nenhum segredo no código |
| `app/database.py` | Engine, `SessionLocal`, `Base`, `get_db` |
| `app/deps.py` | Aliases `Annotated`: `DbSession`, `AppSettings`, `PaginacaoDep` |
| `app/models.py` | Tabelas (SQLAlchemy) — como o dado é **guardado** |
| `app/schemas.py` | Contratos (Pydantic) — o que **entra e sai** da API |
| `app/crud.py` | Operações de banco — a rota não monta query |
| `app/routers/` | Endpoints por domínio |
| `app/services/` | Integrações externas (Blob Storage, e-mail…) |

## Por que stateless

O App Service pode subir várias instâncias. Se o servidor guardar sessão ou carrinho em variável global, a próxima requisição cai em outra máquina que não conhece esse estado.

O estado viaja junto (token no header, id na URL) ou vai para o banco / cache. Assim qualquer instância atende qualquer requisição, e dá para escalar, reiniciar e trocar máquina sem derrubar ninguém.

**Consequência prática:** nunca guarde nada em variável de módulo entre requisições.

## Decisões tomadas

| # | Decisão | Alternativa descartada | Motivo |
|---|---|---|---|
| 1 | FastAPI | Flask, Django REST | Validação nativa, docs automáticos, async, exigência da disciplina |
| 2 | `uv` | venv + pip | Lockfile real, build reproduzível; `uv export` gera o `requirements.txt` do Azure |
| 3 | SQLAlchemy síncrono | SQLModel, driver async | Rotas viram `def` normal (threadpool), sem risco de bloquear o event loop |
| 4 | SQLite local, Azure SQL em produção | Azure SQL sempre | O time desenvolve e roda testes sem credencial nem custo |
| 5 | Blob Storage para arquivos | Coluna BLOB no banco | Binário em banco relacional é caro e não escala |
| 6 | Versionamento `/api/v1/` desde o dia 1 | Adicionar depois | Evoluir sem quebrar cliente já existente |
| 7 | Paginação obrigatória em listagem | Retornar tudo | Funciona com 50 linhas, derruba a instância com 500 mil |
| 8 | OIDC no GitHub Actions | Publish profile | Nenhum segredo de longa duração guardado no GitHub |
| 9 | Azure Static Web Apps para o frontend | Servir estático pelo próprio FastAPI | Padrão de mercado para SPA + API separada; build/deploy próprio via GitHub Actions, CDN e certificado grátis incluídos |
| 10 | Branch padrão `main` | `master` (como o repo nasceu) | Convenção atual do GitHub/mercado; os workflows `ci.yml` e `deploy-azure.yml` já assumiam `main` — renomear corrigiu um bug real (nada disparava) |

> Nova decisão relevante entra aqui, com a alternativa descartada e o motivo.
> Decisão sem motivo escrito vira discussão de novo daqui a três sprints.

## Fluxos

### Criar um recurso

```
POST /api/v1/itens
  → Pydantic valida (falhou? 422, sem escrever um if)
  → crud.criar_item() persiste
  → 201 Created + ItemResponse
```

### Upload de arquivo

```
POST /api/v1/arquivos
  → valida content-type (415) e tamanho (413) ANTES de subir
  → gera nome novo com uuid4 (nunca reusa o nome do cliente)
  → services.storage.salvar() → Blob Storage
  → grava metadados + URL no banco
  → 201 Created
```

### Dashboard

```
GET /api/v1/metricas/resumo
  → GROUP BY no banco (não em Python)
  → ResumoDashboard
```

## Ambientes

| | Local | Azure |
|---|---|---|
| Banco | SQLite (`projeto4.db`) | Azure SQL |
| Arquivos | `./uploads_local/` | Blob Storage |
| Segredos | `.env` (fora do Git) | App Settings → Key Vault |
| Executar | `uv run fastapi dev app/main.py` | `gunicorn` + `UvicornWorker` |
| CORS | `localhost:3000`, `localhost:5173` | domínio real do frontend |

## Diagrama de dados

_(preencher quando as entidades do domínio estiverem definidas — ver `docs/01-requisitos.md`)_
