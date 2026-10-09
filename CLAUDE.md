# Contexto para o agente

Projeto da disciplina **IBM4028 — Projeto em Ciência de Dados IV**, IBMEC CDIA, 2026.2.
Backend FastAPI para Azure App Service + Azure SQL + Blob Storage.

## Estado atual

Domínio real em construção desde 09/10/2026 (retomada do projeto) — cliente é o
Grupo Saints (14 bares/restaurantes), problema prioritário é o delta entre
custo teórico e custo real de compras/estoque (RF02). Entidades: `Casa`
(RF08, CRUD), `UploadCusto` (RF01) e `ItemCusto` (RF02). RF03/RF05 (gestão de
pessoal) seguem adiados até a Conversa 2 com Joyce/Renata/Wellington acontecer.

Plano de sprints em `docs/05-sprints.md`. Board: board "IBM4028 - Grupo Saints"
em [github.com/Lucaslquadros/ibm4028-grupo-saints](https://github.com/Lucaslquadros/ibm4028-grupo-saints).

## Skills deste repositório

Em `.claude/skills/`. Consulte a que corresponde à tarefa **antes** de escrever código:

| Tarefa | Skill |
|---|---|
| Requisitos, personas, user story, MoSCoW, GWT | `requisitos-ibm4028` |
| Endpoint, schema, model, CRUD, teste de API, Azure SQL, Blob | `fastapi-azure-conventions` |
| Deploy, workflow, Docker, App Settings, rollback | `azure-deploy-checklist` |
| Issue, PR, commit, sprint, DoD, entrega parcial | `sprint-delivery-ibm4028` |
| Auth, Key Vault, LGPD, App Insights, alerta | `security-monitoring-checklist` |

## Regras não negociáveis

1. **Nenhum segredo no código.** Tudo via `pydantic-settings` → `.env` local, App Settings no Azure. Nunca cole connection string ou chave em prompt.
2. **Schema ≠ model.** `schemas.py` é o contrato da API; `models.py` é a tabela. Nunca devolva o model direto.
3. **Estilo `Annotated`.** Aliases em `deps.py`. Nunca `= Depends(...)` no default, nunca `...` (Ellipsis), nunca `RootModel`.
4. **Status codes corretos.** 201 ao criar, 204 ao apagar, 404 ao não achar, 422 na validação. Nunca 200 com `null`.
5. **`async def` só onde há `await`.** SQLAlchemy aqui é síncrono, então rotas de banco são `def` normal.
6. **Toda listagem é paginada.** Agregação roda no banco (`GROUP BY`), não em Python.
7. **Teste cobre caminho feliz e erro.** Cada critério GWT de user story vira teste.
8. **`/health` não pode quebrar.** É o que o App Service usa para decidir reiniciar a instância.
9. **Stack trace vai para o log, nunca para a resposta HTTP.**
10. **Nome de arquivo enviado pelo cliente nunca vira nome de blob.** Gere `uuid4`.

## Comandos

```bash
uv sync --all-groups
uv run fastapi dev app/main.py
uv run pytest
uv run ruff check . --fix && uv run ruff format .
uv export --no-dev --no-hashes --format requirements-txt > requirements.txt
```

## Antes de dar uma tarefa por concluída

- `uv run ruff check .` e `uv run pytest` verdes
- Nenhum segredo no diff
- `/docs` continua correto
- Se mudou requisito, `docs/01-requisitos.md` atualizado com o motivo
