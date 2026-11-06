#!/usr/bin/env bash
# Ajustes de nível 1 da fila de `docs/09-uso-da-nuvem.md`.
#
# Quatro correções de configuração, custo zero, nenhuma mexe em código. São as
# de melhor relação risco-removido ÷ esforço de toda a fila — faça estas antes
# de qualquer outra coisa na nuvem.
#
#   1. Always On          — hoje a instância dorme em ~20 min e a primeira
#                           requisição leva 30–60s. É o modo de falha mais
#                           provável de uma apresentação.
#   2. Logs               — hoje appLogs=Off, httpLogs=false. A regra 9 do
#                           projeto manda o stack trace para o log, e não existe
#                           log. Foi assim que o 500 do uploads-custo passou
#                           semanas sem ninguém ver.
#   3. soft delete no Blob— substituir um upload apaga o original do cliente
#                           para sempre. Pré-requisito do RF09: planilha o
#                           cliente reexporta, nota fiscal fotografada não.
#
# `httpsOnly` NÃO está nesta lista: ele já é `true` desde o provisionamento
# (`infra/provisionar.sh`). Uma auditoria anterior o apontou como pendência por
# erro de consulta — `httpsOnly` não existe em `az webapp config show`, só em
# `az webapp show`, e o campo ausente volta como `null`. O passo 4 abaixo apenas
# confirma, de forma idempotente.
#
# Uso:
#   az login --tenant da49a844-e2e3-40af-86a6-c3819d704f49   # escrita exige MFA
#   bash infra/ajustes-nivel-1.sh
#
# Idempotente: rodar duas vezes não causa dano.

set -euo pipefail

GRUPO="rg-projeto4"
APP="app-projeto4-saints2026"
STORAGE="stprojeto4saints2026"
DIAS_SOFT_DELETE=14

# --- Pré-checagem de autenticação -------------------------------------------
# Leitura no Azure funciona com token em cache; ESCRITA exige MFA neste tenant.
# Sem esta checagem, o script morre no primeiro comando com um erro AADSTS de
# dez linhas, e quem rodou conclui que "rodou" — foi o que aconteceu em
# 06/11/2026. Falhar aqui, com instrução clara, é melhor que falhar no meio.
echo "== 0/4 Conferindo permissão de escrita =="
if ! az webapp update -g "$GRUPO" -n "$APP" --https-only true -o none 2>/tmp/az-auth.txt; then
  echo
  echo "ERRO: a sessão do Azure não tem permissão de escrita." >&2
  if grep -q "AADSTS50076\|multi-factor" /tmp/az-auth.txt 2>/dev/null; then
    echo "Motivo: este tenant exige MFA para operações de escrita." >&2
    echo >&2
    echo "  az login --tenant da49a844-e2e3-40af-86a6-c3819d704f49" >&2
    echo >&2
    echo "Depois do login, confirme que a escrita funciona ANTES de rodar de novo:" >&2
    echo "  az webapp update -g $GRUPO -n $APP --https-only true -o none && echo OK" >&2
  else
    echo "Saída do az:" >&2
    cat /tmp/az-auth.txt >&2
  fi
  exit 1
fi
echo "   ok — escrita permitida (e httpsOnly confirmado em true)"

echo "== 1/4 Always On =="
az webapp config set -g "$GRUPO" -n "$APP" --always-on true -o none
echo "   ok"

echo "== 2/4 Logs da aplicação e de HTTP =="
# --level information: erro + aviso + info. 'verbose' enche o disco sem ganho.
# 35 MB / 7 dias é o teto do filesystem do App Service; não há custo extra.
az webapp log config -g "$GRUPO" -n "$APP" \
  --application-logging filesystem \
  --level information \
  --web-server-logging filesystem \
  --detailed-error-messages true \
  --failed-request-tracing true \
  -o none
echo "   ok — a partir de agora: az webapp log tail -g $GRUPO -n $APP"

echo "== 3/4 soft delete no Blob ($DIAS_SOFT_DELETE dias) =="
az storage account blob-service-properties update \
  --account-name "$STORAGE" -g "$GRUPO" \
  --enable-delete-retention true \
  --delete-retention-days "$DIAS_SOFT_DELETE" \
  --enable-container-delete-retention true \
  --container-delete-retention-days "$DIAS_SOFT_DELETE" \
  -o none
echo "   ok"

echo "== 4/4 httpsOnly — já confirmado no passo 0 =="
echo "   ok"

echo
echo "== Conferência =="
az webapp config show -g "$GRUPO" -n "$APP" \
  --query "{alwaysOn:alwaysOn, healthCheck:healthCheckPath}" -o json
az webapp show -g "$GRUPO" -n "$APP" --query "{httpsOnly:httpsOnly}" -o json
az webapp log show -g "$GRUPO" -n "$APP" \
  --query "{appLogs:applicationLogs.fileSystem.level, httpLogs:httpLogs.fileSystem.enabled}" -o json
az storage account blob-service-properties show \
  --account-name "$STORAGE" -g "$GRUPO" \
  --query "{softDelete:deleteRetentionPolicy.enabled, dias:deleteRetentionPolicy.days}" -o json

echo
echo "Esperado: alwaysOn=true, httpsOnly=true, appLogs=Information,"
echo "httpLogs=true, softDelete=true, dias=$DIAS_SOFT_DELETE."
echo
echo "Atenção: Always On e httpsOnly reiniciam a aplicação. Confirme depois:"
echo "  curl -sf https://$APP.azurewebsites.net/health"
