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
│   ├── models.py           Tabelas (SQLAlchemy)  — como o dado é GUARDADO
│   ├── schemas.py          Contratos (Pydantic)  — o que ENTRA e SAI
│   ├── crud.py             Operações de banco
│   ├── routers/            health · itens · uploads · metricas
│   └── services/           storage (Blob Storage / disco local)
├── tests/                  pytest — 28 testes
├── docs/
│   ├── 00-customer-discovery.md   Registro das conversas (Mom Test)
│   ├── 01-requisitos.md           ← Entrega Parcial 1
│   ├── 02-arquitetura.md          Diagrama e decisões
│   └── 03-skills.md               Skills instaladas e a instalar
├── .claude/skills/         5 skills da disciplina
├── .github/workflows/      ci.yml · deploy-azure.yml
├── infra/                  Provisionamento (Bicep / az cli)
├── Dockerfile              Multi-stage, não-root, healthcheck
└── .env.example            Copie para .env
```

## Endpoints

| Método | Rota | Status esperado |
|---|---|---|
| `GET` | `/health` | 200 |
| `GET` | `/api/v1/itens` | 200 — paginado `{total, limit, offset, items}` |
| `GET` | `/api/v1/itens/{id}` | 200 · 404 se não existe · 422 se o id não é número |
| `POST` | `/api/v1/itens` | **201** · 422 se inválido |
| `PATCH` | `/api/v1/itens/{id}` | 200 · 404 |
| `DELETE` | `/api/v1/itens/{id}` | **204** · 404 |
| `POST` | `/api/v1/arquivos` | 201 · 415 tipo · 413 tamanho |
| `GET` | `/api/v1/arquivos` | 200 |
| `GET` | `/api/v1/metricas/resumo` | 200 — alimenta o dashboard |

O recurso `Item` cobre os três itens do MVP mínimo da disciplina: **1 CRUD completo, 1 upload, 1 dashboard**.

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

## Trocar o domínio placeholder

`Item` existe só para o esqueleto rodar. Quando o cliente estiver definido:

1. Preencha `docs/01-requisitos.md` (use a skill `requisitos-ibm4028`)
2. Renomeie `Item` → sua entidade em `models.py`, `schemas.py`, `crud.py`, `routers/itens.py`, `tests/`
3. Renomeie o arquivo `routers/itens.py` e ajuste o `prefix` do `APIRouter`
4. Atualize o `include_router` em `main.py`
5. Rode `uv run pytest` — os testes falham exatamente onde falta ajustar

A estrutura, os status codes, a paginação e o padrão de teste **não mudam**. Só o nome do recurso.

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

Passo a passo completo na skill `azure-deploy-checklist` (`.claude/skills/`). Resumo:

1. `pytest` verde localmente
2. Provisionar App Service + Azure SQL + Storage
3. Configurar App Settings **antes** do primeiro deploy (incluindo `SCM_DO_BUILD_DURING_DEPLOYMENT=true`)
4. Configurar startup command e health check path
5. Deploy manual funcionando
6. Só então o workflow `.github/workflows/deploy-azure.yml` (autenticação OIDC — sem publish profile)

Antes do primeiro deploy, troque `AZURE_WEBAPP_NAME` no workflow e configure as variables `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID` no repositório.

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
