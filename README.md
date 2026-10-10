# Projeto 4 — IBM4028

**Projeto em Ciência de Dados IV | IBMEC CDIA | 2026.2**

API em FastAPI preparada para Azure App Service + Azure SQL + Blob Storage.
O ambiente está montado; o **domínio ainda é placeholder** — troque quando o cliente e o problema estiverem definidos.

---

## Começar em 3 comandos

```bash
uv sync --all-groups
cp .env.example .env
uv run fastapi dev app/main.py
```

| URL | O que é |
|---|---|
| http://localhost:8000/docs | Swagger — teste os endpoints pelo navegador |
| http://localhost:8000/redoc | Documentação de referência |
| http://localhost:8000/openapi.json | Contrato da API |
| http://localhost:8000/health | Health check (é isto que o Azure chama) |

Não precisa instalar banco: o padrão é SQLite em arquivo local.

<details>
<summary>Sem <code>uv</code>? Instale (recomendado) ou use venv + pip</summary>

```powershell
# Windows PowerShell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

```bash
# Linux / macOS
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Alternativa clássica:

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
source .venv/bin/activate       # Linux/macOS
pip install -r requirements.txt
fastapi dev app/main.py
```

O grupo inteiro deve usar **o mesmo** caminho. Misturar os dois gera divergência de versão que só aparece no deploy.
</details>

---

## Estrutura

```
.
├── app/                    Backend
│   ├── main.py             Entrada, CORS, routers, handler de erro
│   ├── config.py           Settings (pydantic-settings) — nenhum segredo no código
│   ├── database.py         Engine, SessionLocal, Base, get_db
│   ├── deps.py             Aliases Annotated: DbSession, AppSettings, Paginacao
│   ├── models.py           Tabelas (SQLAlchemy)  — Casa, UploadCusto, ItemCusto
│   ├── schemas.py          Contratos (Pydantic)  — o que ENTRA e SAI
│   ├── crud.py             Operações de banco
│   ├── routers/            health · casas · uploads · metricas
│   └── services/           storage (Blob Storage / disco local)
├── frontend/               index.html placeholder — React entra na Sprint 2
├── tests/                  pytest — 33 testes
├── docs/
│   ├── 00-customer-discovery.md   Registro das conversas (Mom Test)
│   ├── 01-requisitos.md           Documento de requisitos (RF/RNF, vivo)
│   ├── 02-arquitetura.md          Diagrama e decisões
│   ├── 03-skills.md               Skills instaladas e a instalar
│   ├── 05-sprints.md              Plano de sprints até o MVP
│   └── 06-guia-deploy-azure.md    Passo a passo de deploy, com os comandos
├── .claude/skills/         5 skills da disciplina
├── .github/workflows/      ci.yml · deploy-azure.yml
├── infra/provisionar.sh    App Service + Azure SQL + Storage + Static Web App
├── Dockerfile              Multi-stage, não-root, healthcheck
└── .env.example            Copie para .env
```

## Endpoints

| Método | Rota | Status esperado |
|---|---|---|
| `GET` | `/health` | 200 |
| `GET` | `/api/v1/casas` | 200 — paginado `{total, limit, offset, items}` |
| `GET` | `/api/v1/casas/{id}` | 200 · 404 se não existe · 422 se o id não é número |
| `POST` | `/api/v1/casas` | **201** · 422 se inválido |
| `PATCH` | `/api/v1/casas/{id}` | 200 · 404 |
| `DELETE` | `/api/v1/casas/{id}` | **204** · 404 |
| `POST` | `/api/v1/uploads-custo` | 201 · 404 casa · 415 tipo · 413 tamanho · 422 coluna faltando |
| `GET` | `/api/v1/uploads-custo` | 200 — paginado |
| `GET` | `/api/v1/metricas/delta?casa_id=&periodo=` | 200 — delta custo teórico × real · 404 sem dado |

`Casa` cobre o CRUD do MVP mínimo da disciplina; `uploads-custo` o upload; `metricas/delta` alimenta o dashboard (RF04, Sprint 2).

## Comandos

```bash
uv run fastapi dev app/main.py     # servidor com reload
uv run pytest                      # testes
uv run pytest --cov=app            # com cobertura
uv run ruff check . --fix          # lint
uv run ruff format .               # formatação

# gera o requirements.txt que o Azure App Service instala
uv export --no-dev --no-hashes --format requirements-txt > requirements.txt

docker build -t projeto4-api .
docker run -p 8000:8000 --env-file .env projeto4-api
```

---

## Domínio

Cliente: Grupo Saints (14 bares/restaurantes). Problema prioritário: delta
entre custo teórico e custo real de compras/estoque. Entidades reais —
`Casa`, `UploadCusto`, `ItemCusto` — substituíram o placeholder `Item` na
retomada de 09/10/2026. Detalhes em `docs/01-requisitos.md` e `docs/05-sprints.md`.

---

## Configuração

Nenhum segredo no código. `.env` local (fora do Git), App Settings no Azure, Key Vault para o que é sensível.

| Variável | Padrão | Observação |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./projeto4.db` | Azure SQL exige ODBC Driver 18 + extra `azuresql` |
| `AZURE_STORAGE_CONNECTION_STRING` | vazio | Vazio = uploads em `./uploads_local/` |
| `AZURE_STORAGE_CONTAINER` | `uploads` | |
| `CORS_ORIGINS` | localhost 3000/5173 | Em produção, **nunca** `["*"]` |
| `MAX_UPLOAD_MB` | `10` | |
| `ENVIRONMENT` / `DEBUG` | `local` / `false` | `DEBUG=false` em produção |

Ver `.env.example`.

## Deploy

Guia completo, com os comandos exatos para este repositório (App Service +
Azure SQL + Blob Storage + Static Web App + OIDC): `docs/06-guia-deploy-azure.md`.
Resumo:

1. `pytest` verde localmente
2. Provisionar App Service + Azure SQL + Storage + Static Web App (`infra/provisionar.sh`)
3. Configurar App Settings **antes** do primeiro deploy (incluindo `SCM_DO_BUILD_DURING_DEPLOYMENT=true`)
4. Configurar startup command e health check path
5. Deploy manual funcionando
6. Só então o workflow `.github/workflows/deploy-azure.yml` (autenticação OIDC — sem publish profile)

Antes do primeiro deploy, troque `AZURE_WEBAPP_NAME` no workflow e configure as variables `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID` no repositório.

Branch padrão do repositório: `main` (os workflows disparam em push nesse branch).

## Skills

Cinco skills da disciplina em `.claude/skills/`, versionadas com o código. Ver `docs/03-skills.md` para o que cada uma cobre, as de terceiros a instalar por fase e o que revisar antes de instalar.

---

## Calendário

| Fase | Datas | Entrega |
|---|---|---|
| Definição | agora | Documento de requisitos |
| Backend + BD | 14–28/08 | API com CRUD e banco |
| Oficina 2 | 17/08 | Primeiro deploy no Azure |
| DevOps | 11–18/09 | CI/CD funcionando |
| Qualidade | ~outubro | Segurança e observabilidade |
| MVP | até 09/11 | 1 CRUD + 1 upload + 1 dashboard, no ar |

## Para a Oficina 2 (17/08)

- [x] Ambiente montado e rodando
- [ ] Conta **Azure for Students** ativada (US$ 100, sem cartão)
- [ ] Repositório no GitHub com o grupo todo como colaborador
- [ ] Alguém confirmado no papel de cliente
