---
name: azure-deploy-checklist
description: Publicar a API no Azure App Service e manter o pipeline de deploy do projeto IBM4028 - provisionamento dos recursos, App Settings, autenticação OIDC do GitHub Actions no Azure, workflow de deploy, Docker/ACR, verificação pós-deploy e rollback. Use ao criar ou corrigir workflow de deploy, configurar credencial do Azure no GitHub, montar Dockerfile para App Service, investigar deploy que subiu mas retorna 500 ou 503, ou preparar a Oficina de DevOps. Gatilhos - deploy, App Service, azd, az webapp, GitHub Actions, workflow, OIDC, publish profile, ACR, Dockerfile, container, startup command, rollback, slot, 503, aplicação não sobe.
---

# Checklist de deploy — Azure App Service

Fase de DevOps (11–18/09). Fonte: Aula 04 + práticas das skills `microsoft/azure-skills`, `docker-master` e `github-actions-templates`.

## Ordem que funciona

1. Roda local (`pytest` verde, `/docs` abre)
2. Recursos provisionados no Azure
3. App Settings configuradas **antes** do primeiro deploy
4. Deploy manual funcionando
5. Só então automatizar no GitHub Actions

Pular o passo 4 é a causa nº 1 de "o workflow ficou verde e o site dá 503": você passa a debugar pipeline e aplicação ao mesmo tempo.

## 1. Provisionamento

```bash
az login
az group create -n rg-projeto4 -l brazilsouth

# Plano Linux — F1 é grátis, B1 se precisar de Always On / SSL próprio
az appservice plan create -g rg-projeto4 -n plan-projeto4 --is-linux --sku F1

az webapp create -g rg-projeto4 -p plan-projeto4 \
  -n app-projeto4-<sufixo-unico> --runtime "PYTHON:3.12"
```

O nome vira `https://<nome>.azurewebsites.net` e é global — precisa ser único.

## 2. App Settings (antes do deploy)

```bash
az webapp config appsettings set -g rg-projeto4 -n app-projeto4-<sufixo> --settings \
  ENVIRONMENT=production \
  DEBUG=false \
  DATABASE_URL="mssql+pyodbc://..." \
  AZURE_STORAGE_CONNECTION_STRING="..." \
  CORS_ORIGINS='["https://meu-front.azurestaticapps.net"]' \
  SCM_DO_BUILD_DURING_DEPLOYMENT=true
```

- `SCM_DO_BUILD_DURING_DEPLOYMENT=true` faz o Oryx instalar o `requirements.txt`. Sem isso a app sobe sem dependência e morre no import.
- `CORS_ORIGINS` em produção **nunca** é `["*"]`.
- Segredo sensível vai para o Key Vault e entra como referência `@Microsoft.KeyVault(...)`.

### Startup command

```bash
az webapp config set -g rg-projeto4 -n app-projeto4-<sufixo> \
  --startup-file "gunicorn -w 2 -k uvicorn.workers.UvicornWorker app.main:app --bind 0.0.0.0:8000"
```

O App Service não adivinha o entrypoint de FastAPI. Sem startup command, sobe a página padrão do Azure ou dá 503.

### requirements.txt para o Oryx

O App Service instala a partir de `requirements.txt`, não de `uv.lock`. Gere e versione:

```bash
NO_COLOR=1 uv export --no-dev --no-hashes --format requirements-txt --extra azuresql > requirements.txt
```

Regenere sempre que mexer nas dependências. `requirements.txt` desatualizado = deploy verde com app quebrada.

`--extra azuresql` é obrigatório: `pyodbc` é dependência opcional no `pyproject.toml`
(SQLite local não precisa dele) e some silenciosamente sem essa flag — o build
passa, o gunicorn quebra no boot com `ModuleNotFoundError: No module named 'pyodbc'`.
`NO_COLOR=1` evita que o `uv` grave códigos ANSI de progresso como primeira linha
do arquivo, o que quebra o parse do `pip`/`uv pip install` no Oryx.

### Health check

```bash
az webapp config set -g rg-projeto4 -n app-projeto4-<sufixo> --health-check-path "/health"
```

## 3. Autenticação do GitHub Actions — use OIDC

**Não** use publish profile nem `AZURE_CREDENTIALS` com segredo de longa duração. OIDC não guarda senha nenhuma no GitHub:

```bash
az ad app create --display-name gh-projeto4
# criar service principal, federated credential para
#   repo:<org>/<repo>:ref:refs/heads/main
# e role assignment de Contributor no resource group
```

Guarde apenas três **variáveis** (não segredos): `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID`.

No workflow, o job precisa de:

```yaml
permissions:
  id-token: write   # emitir o token OIDC
  contents: read
```

Sem `id-token: write`, o `azure/login` falha com "no matching federated identity record".

## 4. Workflow

Regras que valem para todo workflow do projeto:

- **`permissions:` explícito** em cada job — o default é amplo demais
- **Ações pinadas por versão** (`@v4`), nunca `@latest` ou `@main`
- **Deploy só depois dos testes**: `needs: [test]`
- **`environment:` com aprovação** para produção — evita deploy acidental
- **Concorrência**: `concurrency: { group: deploy-prod, cancel-in-progress: false }`, para dois merges não deployarem por cima um do outro
- Nada de segredo em `echo` ou em log

O workflow do projeto está em `.github/workflows/deploy-azure.yml`.

## 5. Docker e ACR (opcional, mas valorizado)

Se for por container em vez de código:

- **Multi-stage build**: dependências numa etapa, runtime enxuto na outra
- **Base pinada por versão exata** (`python:3.12-slim-bookworm`), nunca `latest`
- **Usuário não-root** com `USER app` — container rodando como root é achado de segurança
- **`.dockerignore`** com `.venv`, `.git`, `__pycache__`, `.env`, `tests/` — sem ele o contexto de build sobe centenas de MB
- **`HEALTHCHECK`** apontando para `/health`
- Camadas da menos para a mais volátil: copie `pyproject.toml`/`requirements.txt` e instale **antes** de copiar o código, senão todo commit invalida o cache

```bash
az acr create -g rg-projeto4 -n acrprojeto4 --sku Basic
az acr build -r acrprojeto4 -t projeto4-api:$(git rev-parse --short HEAD) .
```

Tagueie com o SHA do commit, não só `latest` — sem tag imutável não existe rollback.

## 6. Verificação pós-deploy (obrigatória)

```bash
curl -sf https://<app>.azurewebsites.net/health   # 200 e banco: "ok"
curl -sf https://<app>.azurewebsites.net/docs
```

Deploy sem verificação automática é deploy que você descobre quebrado pelo cliente. Coloque o `curl /health` como último passo do workflow: se falhar, o job falha.

## 7. Rollback

```bash
# por deployment slot (B1+): troca instantânea, sem downtime
az webapp deployment slot swap -g rg-projeto4 -n <app> --slot staging --target-slot production

# por container: reaponte para a tag anterior
az webapp config container set -g rg-projeto4 -n <app> \
  --docker-custom-image-name acrprojeto4.azurecr.io/projeto4-api:<sha-anterior>
```

Tenha o comando de rollback escrito **antes** do deploy, não durante o incidente.

## Diagnóstico

```bash
az webapp log tail -g rg-projeto4 -n <app>          # log ao vivo
az webapp log deployment show -g rg-projeto4 -n <app>
```

| Sintoma | Causa provável |
|---|---|
| 503 permanente | Falta startup command, ou a app estoura no import |
| "Application Error" | Dependência faltando — `requirements.txt` desatualizado ou `SCM_DO_BUILD` off |
| Sobe e cai em loop | `/health` falhando; App Service reinicia sozinho |
| 500 só em produção | App Setting faltando (`DATABASE_URL`, chave do Blob) |
| Timeout no banco | Firewall do Azure SQL sem o IP / sem "Allow Azure services" |
| CORS no navegador | `CORS_ORIGINS` sem o domínio real do front |
| Funciona local, 500 no Azure | Caminho de arquivo local; no App Service só `/tmp` é gravável |
| "Worker failed to boot" sem traceback de import, build e deploy OK | `-w 2+` workers rodando `create_all()` ao mesmo tempo no cold start; um recebe "already exists" (42S01) e derruba o gunicorn inteiro |
| `ModuleNotFoundError: No module named 'app'` com build OK | Zip montado com `Compress-Archive` (Windows) em vez de `python -m zipfile` — grava `\` em vez de `/`, então não existe pasta no Linux |

Log de deploy verde não prova nada sobre a aplicação. Sempre confirme no `/health`.

## Custo

F1 é grátis mas tem 60 min de CPU/dia e não tem Always On — a app hiberna e a primeira requisição demora. B1 (~US$ 13/mês) resolve. O Azure for Students dá US$ 100 por 12 meses. Configure **alerta de orçamento** em Cost Management no primeiro dia: crédito de estudante acaba silenciosamente.

## Checklist antes de marcar o deploy como pronto

- [ ] `pytest` e `ruff` verdes localmente
- [ ] `requirements.txt` regenerado a partir do `uv.lock`
- [ ] App Settings completos, incluindo `SCM_DO_BUILD_DURING_DEPLOYMENT`
- [ ] Startup command configurado
- [ ] Health check path apontando para `/health`
- [ ] OIDC configurado; nenhum publish profile no repositório
- [ ] Workflow com `permissions:` explícito e ações pinadas
- [ ] `curl /health` como passo final do workflow
- [ ] Comando de rollback documentado no README
- [ ] Alerta de orçamento ativo
- [ ] Nenhum segredo no diff (`git log -p` conferido)
