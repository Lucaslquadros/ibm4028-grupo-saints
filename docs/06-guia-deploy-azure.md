# Guia de deploy — Azure (App Service + Azure SQL + Blob Storage + Static Web App)

**IBM4028 — Projeto 4 | IBMEC CDIA 2026.2**

> Passo a passo para deixar a infraestrutura de Azure configurada na Sprint 1
> (issue [#5](https://github.com/Lucaslquadros/ibm4028-grupo-saints/issues/5)).
> Segue a mesma estrutura do `AC_1/docs/GUIA-DEPLOY.md` — reaproveite os
> "Atenção" de lá, eles valem de novo aqui porque são os mesmos recursos.
>
> **Divisão de trabalho:** os comandos abaixo rodam na SUA conta Azure e no
> SEU GitHub — eu preparei o script e o texto, mas `az login`, criação de
> recurso e configuração de secret/variable precisam ser feitos por você.

---

## 0. O que já foi resolvido antes de você começar

- **Bug do branch corrigido.** O repositório nasceu com branch `master`, mas os
  dois workflows (`ci.yml`, `deploy-azure.yml`) sempre esperaram `main` — nenhum
  deploy automático teria disparado. Já renomeei: `main` é o branch padrão
  agora, local e no GitHub. Decisão alinhada ao padrão de mercado (GitHub usa
  `main` como default desde 2020; Azure DevOps e a doc da Microsoft também).
- **`infra/provisionar.sh` já atualizado** com a seção de Static Web App e com
  `SWA`/`GITHUB_REPO`/`GITHUB_BRANCH` prontos — só falta você preencher `SUFIXO`.
- **`frontend/index.html`** — página placeholder criada só para o Static Web
  App ter algo válido para publicar nesta sprint. O dashboard real (RF04,
  React) substitui este arquivo na Sprint 2.

## 1. Antes de começar

- Conta Azure ativa (Azure for Students — US$ 100, sem cartão)
- `az version` já confirmado nesta máquina (2.90.0 instalado)
- Rode os comandos **no Git Bash**, não no PowerShell nativo. O `infra/provisionar.sh`
  é bash. Isso também evita as Atenção 2/3 do seu guia da AC1 (quebra de `&` e
  `${VAR}` no `cmd.exe`) — elas eram específicas do PowerShell chamando `az`
  direto, e Git Bash não tem esse problema.
- Escolha um `SUFIXO` único (ex.: suas iniciais + 3-4 números) e abra
  `infra/provisionar.sh` para preencher `SUFIXO="TROCAR"`.
- **Nunca cole no chat a saída de um comando que tenha expandido um segredo**
  (senha, connection string). `az ... set` nunca ecoa valor (sempre `null`),
  então é sempre seguro colar. Já `az ... list`, ou um comando que falhou e o
  bash reimprime a linha expandida no erro, pode vazar segredo — aconteceu
  duas vezes rodando este guia. Se isso acontecer, troque a senha depois.

---

## 2. Provisionar os recursos

```bash
cd /c/Faculdade/2026_2/Proj_4/Projeto

az login
az account show --output table

export SQL_PASSWORD='DEFINA-UMA-SENHA-FORTE-AQUI'   # nunca no script, nunca commitada

bash infra/provisionar.sh
```

> **Atenção 1 (herdada da AC1, confirmada de novo aqui) — região pode ser
> bloqueada.** `brazilsouth` e `eastus` vieram `RequestDisallowedByAzure` nesta
> assinatura. `centralus` foi liberado por política, mas o **plano F1 (grátis)
> deu "No available instances"** — erro diferente, de capacidade do tier
> compartilhado, não de política. Solução que funcionou: `centralus` + `B1`
> em vez de F1 (`az appservice plan create ... --sku B1 -l centralus`, ~US$13/mês,
> cobrado por hora). O `infra/provisionar.sh` já está assim. Resource group não
> muda de região depois de criado — se já existir noutra região, não recrie,
> só force a região em cada recurso de dentro com `-l`.
>
> **Atenção 1b — Git Bash "corrige" argumento que começa com `/`.** Qualquer
> argumento tipo `/health` passado pro `az` (programa nativo do Windows) pode
> ser convertido sozinho para um caminho de arquivo (`C:/Program Files/Git/health`)
> — o MSYS escaneia o argumento inteiro, não só confere se ele começa com `/`.
> Aconteceu no `--health-check-path` e persistiu silenciosamente mesmo dentro
> de `--generic-configurations "healthCheckPath=/health"`. Fix: prefixar o
> comando com `MSYS_NO_PATHCONV=1`. Depois de qualquer comando com `/algumacoisa`
> na linha, **confirme com um `show`/`list`** — o comando pode "funcionar" sem
> erro e salvar o caminho errado mesmo assim.

O script, nesta ordem, cria: grupo de recursos → plano App Service (B1, ver
Atenção 1) → Web App → Azure SQL Server + banco + firewall → Storage Account +
container → App Settings → startup command + health check → **Static Web App**
(nova seção, ver abaixo).

### O passo do Static Web App dispara um login separado

```bash
# dentro do provisionar.sh, mas pode rodar isolado se preferir conferir antes:
az staticwebapp create \
  -n "$SWA" -g "$GRUPO" -l "$REGIAO" \
  -s "https://github.com/Lucaslquadros/ibm4028-grupo-saints" -b main \
  --app-location "frontend" --output-location "" \
  --login-with-github
```

Isso abre um **device login do GitHub**: aparece um código de 8 caracteres e
`https://github.com/login/device`. Abra o link, digite o código, autorize —
a Azure CLI:

1. Cria o recurso Static Web App (tier Free, sem custo)
2. Commita **sozinha** um workflow novo em
   `.github/workflows/azure-static-web-apps-<nome-gerado>.yml`
3. Dispara o primeiro build/deploy

Depois disso:

```bash
git pull origin main
```

para trazer esse commit automático para o seu clone.

> **Por que `output-location ""` e sem `app-location` de build:** ainda não
> existe um projeto Vite/React em `frontend/` — só o `index.html` placeholder.
> Sem `package.json`, a Azure detecta "sem framework" e publica o conteúdo da
> pasta como está. Quando o React entrar (Sprint 2, issue
> [#6](https://github.com/Lucaslquadros/ibm4028-grupo-saints/issues/6)), você
> edita esse mesmo workflow para `output_location: "dist"` e adiciona o passo
> de build — não precisa recriar o recurso.

---

## 3. Primeiro deploy do backend — manual, antes de automatizar

Por quê: é o passo que a skill `azure-deploy-checklist` e a sua experiência na
AC1 mais reforçam — "o workflow ficou verde e o site deu 503" é sempre
sintoma de ter pulado o deploy manual antes do automatizado.

```bash
APP=app-projeto4-saints2026   # já criado — ver seção 2

uv export --no-dev --no-hashes --format requirements-txt > requirements.txt

# zipfile do Python em vez de `zip -r`: Git Bash nem sempre tem o binário zip
# instalado, e o uv/python já está garantido (é o mesmo que roda a API).
uv run python -m zipfile -c deploy.zip app requirements.txt

az webapp deploy -g rg-projeto4 -n "$APP" --src-path deploy.zip --type zip
```

> **Atenção 2 (herdada da AC1) — `403` / "This web app is stopped" no Kudu.**
> App Services novos vêm com **SCM Basic Auth Publishing Credentials
> desativado** por padrão. Sem isso o zip deploy nem autentica. Ative:
>
> ```bash
> az resource update --resource-group rg-projeto4 --name scm --namespace Microsoft.Web \
>   --resource-type basicPublishingCredentialsPolicies --parent "sites/${APP}" \
>   --set properties.allow=true
> ```

Confirme:

```bash
curl https://${APP}.azurewebsites.net/health
```

Espere `{"status":"ok", ..., "banco":"ok"}`. Se não vier, veja o log:

```bash
az webapp log tail -g rg-projeto4 -n "$APP"
```

> **Atenção 3 (herdada da AC1) — cota do F1 (60 min CPU/dia).** Se o app parar
> de responder depois de várias rodadas de teste, é isso, não bug seu. Upgrade
> temporário: `az appservice plan update -g rg-projeto4 -n plan-projeto4 --sku B1`
> (cobrado por hora, ~US$0,018/h). Volte para F1 depois:
> `az appservice plan update -g rg-projeto4 -n plan-projeto4 --sku F1`.

---

## 4. OIDC — autenticação do GitHub Actions (isto NÃO existia na AC1)

Na AC1 você logava manualmente com `az login` e rodava tudo na sua sessão. O
workflow `deploy-azure.yml` deste projeto espera login automático via OIDC —
sem senha nem secret de longa duração guardado no GitHub. É a única peça
genuinamente nova em relação à AC1.

```bash
# 1. App registration
APP_ID=$(az ad app create --display-name gh-ibm4028-grupo-saints --query appId -o tsv)

# 2. Service principal ligado ao app registration
az ad sp create --id "$APP_ID"

# 3. Role assignment: Contributor no resource group (não na subscription inteira)
SUBSCRIPTION_ID=$(az account show --query id -o tsv)
az role assignment create --assignee "$APP_ID" --role Contributor \
  --scope "/subscriptions/${SUBSCRIPTION_ID}/resourceGroups/rg-projeto4"

# 4. Federated credential — só aceita token vindo de push no branch main deste repo
az ad app federated-credential create --id "$APP_ID" --parameters '{
  "name": "gh-main-branch",
  "issuer": "https://token.actions.githubusercontent.com",
  "subject": "repo:Lucaslquadros/ibm4028-grupo-saints:ref:refs/heads/main",
  "audiences": ["api://AzureADTokenExchange"]
}'

# 5. IDs que vão virar variáveis (não segredos) no GitHub
echo "AZURE_CLIENT_ID=$APP_ID"
echo "AZURE_TENANT_ID=$(az account show --query tenantId -o tsv)"
echo "AZURE_SUBSCRIPTION_ID=$SUBSCRIPTION_ID"
```

> **Se também quiser aprovar PR vindo de outro branch que não `main`** (ex.:
> para testar o workflow manualmente via `workflow_dispatch` antes do merge),
> crie um segundo federated credential com
> `"subject": "repo:Lucaslquadros/ibm4028-grupo-saints:environment:production"`
> em vez de `ref:refs/heads/main` — cobre o gate do `environment: production`
> do workflow independente do branch de origem.

Configure as três variáveis no repositório (não são secrets — são públicas,
não dão acesso sozinhas sem o federated credential):

```bash
gh variable set AZURE_CLIENT_ID --repo Lucaslquadros/ibm4028-grupo-saints --body "$APP_ID"
gh variable set AZURE_TENANT_ID --repo Lucaslquadros/ibm4028-grupo-saints --body "$(az account show --query tenantId -o tsv)"
gh variable set AZURE_SUBSCRIPTION_ID --repo Lucaslquadros/ibm4028-grupo-saints --body "$SUBSCRIPTION_ID"
```

Troque também o placeholder no workflow:

```bash
# app/.github/workflows/deploy-azure.yml, linha env.AZURE_WEBAPP_NAME
# de: app-projeto4-TROCAR
# para: app-projeto4-<seu SUFIXO>
```

### Ambiente `production` com aprovação manual

Isso é configuração do GitHub, não CLI: **Settings → Environments → New
environment → `production`** → marque **Required reviewers** e adicione você
(ou o grupo). Sem isso, o `environment: production` do workflow passa direto,
sem o portão de aprovação que a skill `azure-deploy-checklist` pede.

---

## 5. Ligar a automação

Depois do deploy manual confirmado e do OIDC configurado, qualquer push em
`main` (ou aprovação manual no environment) dispara o deploy sozinho:

```bash
git add .github/workflows/deploy-azure.yml
git commit -m "chore(deploy): configura AZURE_WEBAPP_NAME real"
git push origin main
```

Acompanhe em **Actions**, ou:

```bash
gh run watch --repo Lucaslquadros/ibm4028-grupo-saints
```

---

## 6. Depois que as duas URLs existirem

Com `https://app-projeto4-<sufixo>.azurewebsites.net` (backend) e
`https://swa-projeto4-<sufixo>.azurestaticapps.net` (frontend) no ar:

1. Confirme que `CORS_ORIGINS` no App Settings já aponta para a URL real do
   Static Web App (o script já preenche isso, mas confira: `az webapp config
   appsettings list -g rg-projeto4 -n "$APP" --query "[?name=='CORS_ORIGINS']"`)
2. Teste CORS de verdade, simulando o navegador:
   ```bash
   curl -i -X OPTIONS https://app-projeto4-<sufixo>.azurewebsites.net/api/v1/casas \
     -H "Origin: https://swa-projeto4-<sufixo>.azurestaticapps.net" \
     -H "Access-Control-Request-Method: GET"
   ```
   Espere `200` com `Access-Control-Allow-Origin` no header.

---

## 7. Alerta de orçamento (não deixe para depois)

Via CLI de budget o JSON de notificação é verboso e tende a falhar silencioso
em assinatura de estudante. Mais confiável pelo portal:

**Portal Azure → Cost Management + Billing → Budgets → Add** → defina um
budget mensal (ex.: US$ 20, bem abaixo do crédito total) com alerta em 80% e
100% por e-mail. Crédito de estudante acaba silenciosamente — isso é o que
evita descobrir isso tarde.

---

## Checklist desta sprint

- [ ] Branch `main` confirmado como default (feito)
- [ ] `SUFIXO` escolhido e preenchido em `infra/provisionar.sh`
- [ ] Resource group, App Service, Azure SQL, Storage criados
- [ ] App Settings aplicadas, incluindo `CORS_ORIGINS` com a URL do Static Web App
- [ ] Startup command + health check configurados
- [ ] SCM Basic Auth ativado (Atenção 2)
- [ ] Deploy manual confirmado (`/health` responde 200 em produção)
- [ ] Static Web App criado, primeiro build publicado
- [ ] OIDC configurado (App registration + federated credential + role assignment)
- [ ] 3 variáveis (`AZURE_CLIENT_ID`/`TENANT_ID`/`SUBSCRIPTION_ID`) no GitHub
- [ ] `AZURE_WEBAPP_NAME` real no workflow (sem `TROCAR`)
- [ ] Environment `production` com required reviewer configurado
- [ ] Push em `main` disparou o deploy automático e passou
- [ ] CORS testado com `curl -X OPTIONS`, não só "parece funcionar"
- [ ] Alerta de orçamento ativo no portal
- [ ] Nenhum segredo commitado (`git log --all -p -- '*.env'` conferido)

## Resumo: o que é igual e o que é novo em relação à AC1

| Item | AC1 | Este projeto |
|---|---|---|
| App Service, Azure SQL, Blob Storage | Mesmos recursos, mesmo tier | Idêntico |
| Static Web App | Sim, `--login-with-github` | Idêntico, mesma CLI |
| Atenção região / SCM Basic Auth / cota F1 | Sim | Mesmos riscos, mesma solução |
| Autenticação do deploy | Manual (`az login` na sua sessão) | **OIDC** — novo, seção 4 |
| Branch do repositório | Não era um problema (repo não tinha workflow) | **Era `master`, corrigido para `main`** |
