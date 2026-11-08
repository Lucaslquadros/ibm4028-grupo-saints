# Contexto para o agente

Projeto da disciplina **IBM4028 — Projeto em Ciência de Dados IV**, IBMEC CDIA, 2026.2.
Backend FastAPI para Azure App Service + Azure SQL + Blob Storage.

## Estado atual

Domínio real em construção desde 09/10/2026 (retomada do projeto) — cliente é o
Grupo Saints (14 bares/restaurantes), problema prioritário é o delta entre
custo teórico e custo real (RF02). Entidades: `Casa` (RF08, CRUD),
`UploadCusto` (RF01, com `tipo` = `cardapio` | `compras`) e `LinhaCusto` (linhas
extraídas dos exports reais do Everest pelos tradutores em
`app/services/leitores.py`). O MVP é o **fechamento de CMV** de uma casa piloto
(Boteco São Bento - Vila Madalena) — regra do cálculo em `docs/07-fechamento-cmv.md`.
RF03/RF05 (gestão de pessoal) seguem adiados.

**Personas (desde 07/11/2026):** a analista de custos (Persona 1) alimenta o
sistema; o sócio/diretor (Persona 2) lê o resultado e decide. A Persona 3
(pequeno negócio) é hipótese futura, **não** é alvo. O público é quem tem ficha
técnica e inventário mensal — o contrato de entrada está em
`docs/07-fechamento-cmv.md`, "O que o usuário precisa fornecer". As casas
"(DEMO)" provam formato e regra genéricos, não mercado.

## Ciclo atual: 07/11 a 09/11/2026 (apresentação na segunda)

**Leia `docs/11-ciclo-explicacao-do-ajuste.md` inteiro antes de escrever código.**
É a especificação: decisões, contrato da API, testes, ordem de corte.

- **Ciclo concluído em 07/11: os cinco itens estão entregues e no ar** (commit
  `a7fa9c5`), com `/health` e o fechamento de set/26 conferidos. Docs `01`, `07`,
  `08` e `11` já refletem isso.
- Ordem executada: P0 (nomes de grupo + planilha-modelo) → RF11 backend → RF11 tela → RF12 → RF13.
- O ajuste da casa real é **negativo** (−3,68 pp): todo texto tem três ramos (acima / dentro / abaixo). Negativo **não** é economia.
- Abaixo do grupo, só se compara subgrupo que existe nos dois lados. Não inventar granularidade.
- Campos novos na API são **opcionais**: o frontend em produção não pode quebrar entre deploys. Backend primeiro, depois front.
- Nunca usar a casa piloto em 09/2026 para testar envio: reenvio **substitui** o dado real.
- Congelamento: nada de deploy depois de domingo 08/11, 20h. Após cada deploy: `/health` com o SHA novo e fechamento de set/26 com `ajuste_pp: -3.68`.
- **Próximo passo, especificado e não implementado:** RF14 (download do original por SAS) e, depois dele, RF09 (nota fiscal como prova do lado real). Ver `docs/11-…` §8. Imagem só com função: validar por magic bytes (JPEG/PNG/WebP; SVG recusado) e remover EXIF no navegador.
- Fora do ciclo entregue: mini-ERP, alertas, delta semanal, autenticação, infra.

**Dados reais do cliente nunca vão para o Git** (`dados_reais/`, `*.xlsx` no
`.gitignore`). Testes usam planilhas sintéticas de `tests/planilhas.py`.

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
NO_COLOR=1 uv export --no-dev --no-hashes --format requirements-txt --extra azuresql > requirements.txt
```

## Antes de dar uma tarefa por concluída

- `uv run ruff check .` e `uv run pytest` verdes
- Nenhum segredo no diff
- `/docs` continua correto
- Se mudou requisito, `docs/01-requisitos.md` atualizado com o motivo
- Item do ciclo entregue → marcado como entregue em `docs/01-requisitos.md` e `docs/11-…`, e o roteiro `docs/08-roteiro-demo.md` só descreve o que está no ar
