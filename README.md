# Projeto 4 — IBM4028

**Projeto em Ciência de Dados IV | IBMEC CDIA | 2026.2**

Automatiza o **fechamento de CMV** de bares e restaurantes: o relatório que a
equipe de custos do cliente monta à mão, cruzando três módulos do ERP, em cerca
de **2 dias por casa por mês**.

O sistema lê os exports como eles saem do ERP, cruza o custo teórico (ficha
técnica × vendas) com o custo real (estoque inicial + compras − estoque final)
e mostra onde está a divergência. Na base real do cliente só há compras (sem
inventário): mês a mês, compras × teórico oscila de −7,2 a +9,3 pp, e somando
jun–dez/22 a diferença é de +0,48 pp, concentrada em alimentos. Por isso o
sistema separa compras de consumo e mostra o acumulado.

## Está no ar

| | |
|---|---|
| **Aplicação** | https://zealous-river-0b6019910.6.azurestaticapps.net |
| **API** | https://app-projeto4-saints2026.azurewebsites.net |
| **Documentação da API** | https://app-projeto4-saints2026.azurewebsites.net/docs |
| **Health check** | https://app-projeto4-saints2026.azurewebsites.net/health — informa o SHA publicado |

Azure App Service + Azure SQL + Blob Storage + Static Web Apps, com deploy
automático por GitHub Actions (OIDC, sem segredo de longa duração).
Para ver funcionando sem instalar nada: `docs/08-roteiro-demo.md`.

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
│   ├── models.py           Tabelas (SQLAlchemy)  — Casa, UploadCusto, LinhaCusto
│   ├── schemas.py          Contratos (Pydantic)  — o que ENTRA e SAI
│   ├── crud.py             Operações de banco
│   ├── routers/            health · casas · uploads · metricas
│   └── services/
│       ├── leitores.py     Tradutores → LinhaCusto (Everest ×2 + planilha genérica)
│       └── storage.py      Blob Storage / disco local
├── frontend/               React + Vite — Casas, Upload, Fechamento, Quanto comprar
├── tests/                  pytest — 107 testes
├── exemplos/               CSV de 4 empresas fictícias (farmácia, padaria, pizzaria, atacado)
├── scripts/
│   ├── importar_exports.py      Importa os exports reais (direto no banco)
│   └── popular_demo_generico.py Carrega as unidades de demo, pela API
├── docs/
│   ├── 00-customer-discovery.md   Registro das conversas (Mom Test)
│   ├── 01-requisitos.md           Documento de requisitos (RF/RNF, vivo)
│   ├── 02-arquitetura.md          Diagrama e decisões
│   ├── 03-skills.md               Skills instaladas e a instalar
│   ├── 04-roteiro-de-teste.md     Como testar a API de 4 formas
│   ├── 05-sprints.md              Plano de sprints até o MVP
│   ├── 06-guia-deploy-azure.md    Passo a passo de deploy, com os comandos
│   ├── 07-fechamento-cmv.md       A regra do cálculo de CMV
│   ├── 08-roteiro-demo.md         Roteiro da apresentação, 100% na nuvem
│   ├── 09-uso-da-nuvem.md         Auditoria dos recursos Azure + fila de ajustes
│   └── 10-anexos-de-imagem.md     RF09/RF10 — especificados, não implementados
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
| `POST` | `/api/v1/fechamentos` | 201 — planilha-modelo de fechamento, um ou vários meses · 404 casa · 415 tipo · 413 tamanho · 422 com a lista de erros por linha |
| `GET` | `/api/v1/fechamentos` | 200 — paginado |
| `GET` | `/api/v1/modelos/fechamento` | 200 — planilha-modelo `.xlsx` |
| `GET` | `/api/v1/metricas/fechamento?casa_id=&periodo=` | 200 — CMV teórico × real × ajuste por grupo · 404 sem dado |
| `GET` | `/api/v1/metricas/evolucao?casa_id=` | 200 — CMV teórico × real mês a mês |
| `GET` | `/api/v1/metricas/top-itens?casa_id=&periodo=` | 200 — itens que mais pesam no custo |

`Casa` cobre o CRUD do MVP mínimo da disciplina; `uploads-custo` lê os exports reais do Everest (ver `docs/07-fechamento-cmv.md`); `metricas/*` alimenta o dashboard de fechamento, consumido pelo frontend em `frontend/`.

## Comandos

```bash
uv run fastapi dev app/main.py     # servidor com reload
uv run pytest                      # testes
uv run pytest --cov=app            # com cobertura
uv run ruff check . --fix          # lint
uv run ruff format .               # formatação

# gera o requirements.txt que o Azure App Service instala
# --extra azuresql traz o pyodbc, obrigatório em produção (DATABASE_URL é mssql+pyodbc)
NO_COLOR=1 uv export --no-dev --no-hashes --format requirements-txt --extra azuresql > requirements.txt

docker build -t projeto4-api .
docker run -p 8000:8000 --env-file .env projeto4-api
```

---

## Domínio

Cliente: Grupo Saints (14 bares/restaurantes). Problema prioritário: o delta
entre custo teórico e custo real. Entidades: `Casa` (RF08), `UploadCusto`
(RF01) e `LinhaCusto` — a linha canônica que todos os tradutores produzem.
A regra do cálculo está em `docs/07-fechamento-cmv.md`.

**Desde 06/11/2026 o cliente é caso de estudo, não PO ativo** (parou de
responder após a Conversa 2). O que o projeto passou a sustentar é uma tese
verificável, e não a aprovação de um PO:

> O cálculo de fechamento é agnóstico à origem do dado e ao ramo do negócio.
> Adaptar a um novo ERP é escrever **um tradutor**, não mexer na regra; e as
> categorias que formam o CMV são **deduzidas do dado**, não configuradas.

Duas consequências disso no código, as duas testadas em
`tests/test_generalizacao.py`:

- `app/services/leitores.py` tem um terceiro tradutor, que lê uma tabela comum
  (`grupo`, `custo` e colunas opcionais) em vez de um relatório do Everest. O
  formato é **detectado** — o usuário só diz se o arquivo é o lado teórico ou o
  real.
- `crud.grupos_comparaveis` substituiu a constante `("ALIMENTOS", "BEBIDAS")`:
  comparável é o grupo que os **dois** lados do fechamento reportam. Na base
  real isso devolve exatamente ALIMENTOS e BEBIDAS, com os mesmos números de
  antes, sem cravar categoria de restaurante no código.

A demonstração dessa tese usa uma farmácia
(`scripts/popular_demo_generico.py`): outro ramo, outras categorias, planilha
genérica. **Dado fictício, rotulado "(DEMO)"** — nunca se confunde com a casa
piloto real.

As limitações conhecidas (incluindo a proveniência não provada da DRE real)
estão em `docs/01-requisitos.md`, seção 1.9.

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

| Fase | Datas | Entrega | Estado |
|---|---|---|---|
| Definição | ago/set | Documento de requisitos (AC2, 21/09) | Entregue |
| Backend + BD | ago | API com CRUD e banco | Entregue |
| Retomada de domínio | 09/10 | `Casa`, `UploadCusto`, `LinhaCusto` no lugar do placeholder | Entregue |
| Primeiro deploy no Azure | out | App Service + SQL + Blob + Static Web App no ar | Entregue |
| DevOps | out | CI/CD por GitHub Actions com OIDC | Entregue |
| Exports reais + fechamento | 03/11 | Tradutores do Everest e cálculo de CMV | Entregue |
| Frontend | 05/11 | React no Static Web Apps (RF04) | Entregue |
| Generalização | 06/11 | Tradutor agnóstico de ERP + dedução de grupos, 4 ramos em produção | Entregue |
| RF07 | 06/11 | Recomendação de compra: endpoint + tela | Entregue |
| Infra nível 1 | 06/11 | Always On, logs, soft delete; CI/CD publicando de fato | Entregue |
| Qualidade | — | Autenticação (RNF03) e Application Insights | **Não entregue** |
| MVP | até 09/11 | 1 CRUD + 1 upload + 1 dashboard, no ar | Entregue |

## Para a apresentação

Roteiro completo, sem instalar nada: **`docs/08-roteiro-demo.md`**.
