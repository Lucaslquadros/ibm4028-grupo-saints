# Skills do projeto — o que está instalado e o que instalar

Duas categorias: as **personalizadas** (escritas para esta disciplina, já dentro do repositório) e as **de terceiros** (instaladas por comando, revisadas antes de usar).

---

## 1. Personalizadas — já no repositório

Ficam em `.claude/skills/<nome>/SKILL.md`. Versionadas junto com o código, então valem para o grupo inteiro e evoluem via PR.

| Skill | Cobre | Fase |
|---|---|---|
| `requisitos-ibm4028` | 10 seções do documento, personas, RF/RNF, user story, GWT, MoSCoW, Mom Test | Definição (agora) |
| `fastapi-azure-conventions` | Estrutura, schemas × models, estilo `Annotated`, status codes, paginação, Azure SQL, Blob | Backend + BD (14–28/08) |
| `azure-deploy-checklist` | Provisionamento, App Settings, OIDC, workflow, Docker/ACR, verificação, rollback | DevOps (11–18/09) |
| `sprint-delivery-ibm4028` | Issue como user story, DoD, commit, PR, ritmo da sprint, entrega parcial | DevOps |
| `security-monitoring-checklist` | Key Vault, managed identity, JWT, LGPD, App Insights, alertas, custo | Qualidade (~outubro) |

Como usar: descreva a tarefa normalmente ("preciso criar o endpoint de listagem de pedidos") — a skill correspondente é acionada pela descrição. Para forçar, cite o nome.

---

## 2. De terceiros — instalar quando chegar a fase

> **Nenhuma destas é da Anthropic.** Antes de rodar qualquer uma, abra o `SKILL.md` instalado e leia — principalmente as que empacotam script ou MCP server. Skill é instrução que o agente segue; script empacotado é código que executa na sua máquina.

### 2.1 `fastapi/fastapi` — skill oficial do time FastAPI

```bash
npx skills add fastapi/fastapi --skill fastapi --agent claude-code
```

Instala em `.claude/skills/`. Conteúdo: `Annotated` para parâmetros e dependências, evitar Ellipsis e `RootModel`, `response_model` × tipo de retorno, `async` × `def`, inclusão de routers, streaming (JSON Lines, SSE, bytes), dependências com `yield` e escopos. Traz arquivos de referência (`streaming.md`, `dependencies.md`, `responses.md`, `pydantic.md`, `path-operations.md`, `other-tools.md`).

**Risco:** baixo — documentação, sem script executável. Exige `npx` (Node 18+).

**Já aplicado neste repositório:** as convenções de `Annotated`, ausência de Ellipsis, `def` por padrão e prefix/tags no `APIRouter` estão implementadas em `app/` e escritas em `fastapi-azure-conventions`. A skill oficial vale como complemento, principalmente para streaming/SSE, que este projeto ainda não usa.

### 2.2 `microsoft/azure-skills` — pacote oficial Microsoft

```
/plugin install azure@claude-plugins-official
```

O pacote é bem maior do que os três sub-skills previstos. Os relevantes para este projeto:

| Sub-skill | Uso aqui |
|---|---|
| `azure-prepare` | Gera `azure.yaml`, Bicep, Dockerfile |
| `azure-validate` | Checagem pré-deploy |
| `azure-deploy` | Executa `azd up` |
| `appinsights-instrumentation` | Fase de Qualidade |
| `azure-cost` | Vigiar o crédito de estudante |
| `azure-diagnostics` | Quando o deploy sobe e dá 503 |

**Risco: o mais alto dos quatro.** O plugin embarca o **Azure MCP Server** (200+ ferramentas sobre 40+ serviços) e `azure-deploy` roda `azd up` — que **provisiona recursos reais e gera custo**. Exige Node 18+, `az login` e `azd auth login`.

**Recomendação:** instale só na fase de DevOps. Rode `azure-prepare` e `azure-validate` primeiro e **leia o que foi gerado** antes de deixar qualquer coisa executar `azd up`. Com US$ 100 de crédito e sem cartão, provisionar tier errado consome o semestre inteiro em dias.

### 2.3 `docker-master` — JosiahSiegel/claude-plugin-marketplace

```
/plugin marketplace add JosiahSiegel/claude-plugin-marketplace
/plugin install docker-master@claude-plugin-marketplace
```

Sub-skills: `docker-best-practices`, `docker-platform-guide`, `compose-patterns-2025`. Licença MIT. Cobre build, debug, otimização, Compose, segurança de container, rede e registry.

**Risco:** baixo para as skills em si (não empacotam script executável), mas o marketplace como um todo é 47% shell e 16% PowerShell — confira o que veio antes de rodar qualquer coisa.

**Já aplicado neste repositório:** multi-stage build, base pinada por versão exata, usuário não-root, `HEALTHCHECK`, `.dockerignore` e ordenação de camadas do menos ao mais volátil já estão no `Dockerfile` e documentados em `azure-deploy-checklist`.

### 2.4 `github-actions-templates` — wshobson/agents

```
/plugin marketplace add wshobson/agents
/plugin install cicd-automation@agents
```

Templates de workflow para teste com matriz, build e push de imagem Docker, deploy, e scan de segurança (Trivy, Snyk). Referencia assets em `assets/*.yml`. Boas práticas que ele enforça e que valem para nós: `permissions` explícito, ações pinadas por versão, `environment` como portão de aprovação, workflows reutilizáveis.

**Ressalva:** os exemplos são muito voltados a Node.js, Kubernetes e AWS (EKS, credenciais estáticas da AWS). O nosso alvo é Azure App Service com OIDC. **Não copie o padrão de credencial dele** — chave estática é exatamente o que o OIDC existe para eliminar.

**Já aplicado neste repositório:** `permissions` explícito por job, ações pinadas, `needs: [testes]` como portão, `environment: production` com aprovação, `concurrency` e verificação pós-deploy já estão em `.github/workflows/`.

---

## 3. Sequenciamento

| Fase | Datas | Ativar |
|---|---|---|
| Definição | agora | `requisitos-ibm4028` |
| Backend + BD | 14–28/08 | `fastapi-azure-conventions`, `fastapi/fastapi` |
| DevOps | 11–18/09 | `azure-deploy-checklist`, `sprint-delivery-ibm4028`, `azure-skills`, `docker-master`, `github-actions-templates` |
| Qualidade | ~outubro | `security-monitoring-checklist`, `appinsights-instrumentation` |

Instalar tudo de uma vez atrapalha: skill demais competindo pelo mesmo gatilho piora a escolha do agente. Instale por fase.

---

## 4. Antes de instalar qualquer skill de terceiro

- [ ] Abrir o `SKILL.md` e ler o que ele manda o agente fazer
- [ ] Conferir se empacota script, hook ou MCP server — e o que esses executam
- [ ] Conferir se algum comando **provisiona recurso pago** (`azd up`, `az ... create`)
- [ ] Conferir se pede credencial, e de que tipo (OIDC é aceitável; chave estática, não)
- [ ] Rodar primeiro num branch descartável, não na `main`
