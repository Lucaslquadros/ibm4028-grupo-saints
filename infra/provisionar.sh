#!/usr/bin/env bash
# Provisionamento dos recursos no Azure.
#
# NÃO execute às cegas: cada `create` gasta crédito. Leia, ajuste as variáveis,
# rode um comando de cada vez e confira no portal.
# Detalhes e diagnóstico: .claude/skills/azure-deploy-checklist/SKILL.md

set -euo pipefail

# ----------------------------------------------------------------- ajuste
GRUPO="rg-projeto4"
REGIAO="centralus"                    # brazilsouth bloqueado nesta assinatura
                                       # (RequestDisallowedByAzure) — se centralus
                                       # também falhar, tente eastus / westus2
SUFIXO="TROCAR"                       # precisa ser único globalmente (iniciais+números)
PLANO="plan-projeto4"
APP="app-projeto4-${SUFIXO}"
STORAGE="stprojeto4${SUFIXO}"         # só minúsculas e números, 3-24 chars
SQL_SERVER="sql-projeto4-${SUFIXO}"
SQL_DB="projeto4"
SQL_USER="adminprojeto4"
SWA="swa-projeto4-${SUFIXO}"
GITHUB_REPO="Lucaslquadros/ibm4028-grupo-saints"
GITHUB_BRANCH="main"
# Senha NÃO fica aqui. Exporte antes:  export SQL_PASSWORD='...'
: "${SQL_PASSWORD:?defina SQL_PASSWORD no ambiente antes de rodar}"

# ------------------------------------------------------------------ login
az login
az account show --output table

# --------------------------------------------------------- grupo e plano
# Idempotente: um resource group não "move" de região depois de criado — se
# já existir (em QUALQUER região), reusa; só cria do zero se realmente faltar.
az group show -n "$GRUPO" &>/dev/null || az group create -n "$GRUPO" -l "$REGIAO"

# F1 é grátis: 60 min de CPU/dia, sem Always On. B1 (~US$13/mês) para produção.
# -l "$REGIAO" é OBRIGATÓRIO aqui: sem ele, o plano herda a região do resource
# group (que pode ser outra, ex. brazilsouth bloqueada) em vez da região liberada.
az appservice plan create -g "$GRUPO" -n "$PLANO" --is-linux --sku F1 -l "$REGIAO"

az webapp create -g "$GRUPO" -p "$PLANO" -n "$APP" --runtime "PYTHON:3.12"

# --------------------------------------------------------------- Azure SQL
az sql server create -g "$GRUPO" -n "$SQL_SERVER" -l "$REGIAO" \
  --admin-user "$SQL_USER" --admin-password "$SQL_PASSWORD"

# Basic é o tier mais barato. Serverless GP economiza mais se o uso for esporádico.
az sql db create -g "$GRUPO" -s "$SQL_SERVER" -n "$SQL_DB" \
  --service-objective Basic --backup-storage-redundancy Local

# Sem esta regra, o App Service não conecta no banco.
az sql server firewall-rule create -g "$GRUPO" -s "$SQL_SERVER" \
  -n permitir-servicos-azure --start-ip-address 0.0.0.0 --end-ip-address 0.0.0.0

# Libere também o IP de quem for desenvolver:
# az sql server firewall-rule create -g "$GRUPO" -s "$SQL_SERVER" \
#   -n meu-ip --start-ip-address <IP> --end-ip-address <IP>

# ----------------------------------------------------------- Blob Storage
az storage account create -g "$GRUPO" -n "$STORAGE" -l "$REGIAO" \
  --sku Standard_LRS --kind StorageV2 --min-tls-version TLS1_2

az storage container create --account-name "$STORAGE" -n uploads

STORAGE_CS=$(az storage account show-connection-string \
  -g "$GRUPO" -n "$STORAGE" --query connectionString -o tsv)

# ------------------------------------------------------------ App Settings
DB_URL="mssql+pyodbc://${SQL_USER}:${SQL_PASSWORD}@${SQL_SERVER}.database.windows.net:1433/${SQL_DB}?driver=ODBC+Driver+18+for+SQL+Server&Encrypt=yes&TrustServerCertificate=no"

az webapp config appsettings set -g "$GRUPO" -n "$APP" --settings \
  ENVIRONMENT=production \
  DEBUG=false \
  DATABASE_URL="$DB_URL" \
  AZURE_STORAGE_CONNECTION_STRING="$STORAGE_CS" \
  AZURE_STORAGE_CONTAINER=uploads \
  CORS_ORIGINS="[\"https://${SWA}.azurestaticapps.net\"]" \
  SCM_DO_BUILD_DURING_DEPLOYMENT=true

# Sem startup command o App Service não sabe subir FastAPI → 503.
az webapp config set -g "$GRUPO" -n "$APP" \
  --startup-file "gunicorn -w 2 -k uvicorn.workers.UvicornWorker app.main:app --bind 0.0.0.0:8000"

az webapp config set -g "$GRUPO" -n "$APP" --health-check-path "/health"
az webapp update -g "$GRUPO" -n "$APP" --https-only true

echo
echo "Pronto: https://${APP}.azurewebsites.net"
echo "Confira o health:  curl https://${APP}.azurewebsites.net/health"

# --------------------------------------------------- Static Web App (frontend)
# Free tier, sem custo. --login-with-github abre um device login (código +
# link) e, ao autorizar, a Azure CLI injeta sozinha um workflow
# .github/workflows/azure-static-web-apps-<nome>.yml direto no repositório
# (um commit automático) e dispara o primeiro build.
#
# App Service Plan free (F1) não tem relação com o tier do Static Web App —
# são recursos e cobranças independentes.
az staticwebapp create \
  -n "$SWA" -g "$GRUPO" -l "$REGIAO" \
  -s "https://github.com/${GITHUB_REPO}" -b "$GITHUB_BRANCH" \
  --app-location "frontend" --output-location "" \
  --login-with-github

echo
echo "git pull depois do comando acima — a Azure CLI commitou o workflow."
echo "Frontend (depois do 1º build): https://${SWA}.azurestaticapps.net"
echo
echo "Próximo passo: configurar o alerta de orçamento em Cost Management."
echo "Crédito de estudante acaba silenciosamente."
