---
name: security-monitoring-checklist
description: Segurança, autenticação e observabilidade da aplicação IBM4028 no Azure - Key Vault e managed identity, autenticação JWT e hash de senha, LGPD e dados pessoais, HTTPS e headers, rate limiting, Application Insights, logging estruturado, métricas, alertas e custos. Use ao implementar login, proteger endpoint, mover segredo para o Key Vault, instrumentar a aplicação, configurar alerta, investigar incidente, ou revisar o projeto na fase de Qualidade. Gatilhos - autenticação, JWT, OAuth, senha, hash, Key Vault, managed identity, LGPD, dado pessoal, criptografia, rate limiting, Application Insights, log, métrica, alerta, observabilidade, tracing, SRE, auditoria.
---

# Segurança e observabilidade — IBM4028

Fase de Qualidade (~outubro). Fonte: Aulas 01, 03 e 04 + práticas de `azure-skills` / `appinsights-instrumentation`.

## Responsabilidade compartilhada

| Azure cuida | Você cuida |
|---|---|
| Patch de SO, load balancer, SSL/TLS, infra física, criptografia em repouso do serviço | Código, dependências, **configuração**, autenticação, autorização, validação de input, o que você loga |

Quase todo incidente em projeto de faculdade cai do lado direito — e a maioria é configuração.

## 1. Segredos

**Nível 0 — nunca.** Segredo em código, em commit, em print de tela, em prompt de IA. Se vazou num commit, trocar o segredo é obrigatório: reescrever histórico não basta, o valor já foi exposto.

**Nível 1 — App Settings.** Criptografado em repouso, fora do repositório. É o mínimo aceitável para a entrega.

**Nível 2 — Key Vault + managed identity.** Alvo da fase de Qualidade.

```bash
az keyvault create -g rg-projeto4 -n kv-projeto4 --enable-rbac-authorization true
az keyvault secret set --vault-name kv-projeto4 -n database-url --value "mssql+pyodbc://..."

# managed identity: a app se autentica sem senha nenhuma
az webapp identity assign -g rg-projeto4 -n <app>
az role assignment create --role "Key Vault Secrets User" \
  --assignee <principalId> --scope <id-do-keyvault>
```

Depois, a App Setting vira referência — o valor nunca transita pelo GitHub:

```
DATABASE_URL = @Microsoft.KeyVault(SecretUri=https://kv-projeto4.vault.azure.net/secrets/database-url/)
```

**Managed identity elimina a senha.** Onde der para usar, use: `DefaultAzureCredential()` no lugar de connection string do Blob e do SQL.

Adicione **rotação**: um segredo criado no início do semestre e nunca trocado é dívida, mesmo que nunca vaze.

## 2. Autenticação e autorização

- **Senha nunca em texto puro.** Hash com `bcrypt` ou `argon2` — nunca MD5/SHA1, nunca "criptografia própria".
- **JWT** com expiração curta (15–60 min) e refresh token. Guarde o segredo de assinatura no Key Vault.
- **Autenticação ≠ autorização.** Saber quem é a pessoa não diz o que ela pode fazer. Cheque a permissão **em cada endpoint**, não só no login.
- **IDOR é o furo mais comum**: `GET /api/v1/pedidos/42` que devolve o pedido de outro usuário porque ninguém conferiu o dono. Todo endpoint que recebe id precisa validar propriedade.
- Erro de login é sempre **401 genérico** ("credenciais inválidas"). Dizer "usuário não existe" entrega lista de usuários válidos.
- Alternativa pronta: Azure AD B2C / Entra External ID, se o grupo não quiser manter autenticação própria.

No FastAPI, aplique a dependência de auth no `APIRouter` inteiro, não rota a rota — assim ninguém esquece a nova rota.

## 3. LGPD

Se o projeto toca em nome, CPF, e-mail, telefone, endereço, foto ou dado de saúde, LGPD se aplica. O mínimo:

- **Base legal** declarada em `docs/01-requisitos.md` (consentimento? execução de contrato? legítimo interesse?)
- **Minimização** — não colete campo que o sistema não usa. Cada campo a mais é risco a mais.
- **Criptografia** em trânsito (HTTPS, obrigatório) e em repouso (Azure SQL TDE liga por padrão)
- **Direito de exclusão** — precisa existir caminho para apagar dado de um titular
- **Retenção** — por quanto tempo o dado fica? Defina e implemente
- **Log não guarda dado pessoal.** CPF em log é vazamento com data e hora. Mascare.
- Dado de saúde e biométrico são **sensíveis**: exigência maior. Pense duas vezes antes de escolher esse domínio.

## 4. Aplicação

- **HTTPS only**: `az webapp update -g rg-projeto4 -n <app> --https-only true`
- **CORS** com o domínio real. `["*"]` em produção é achado de segurança.
- **Validação de input** via Pydantic — já cobre injeção pela borda
- **SQL injection**: use sempre o ORM ou parâmetros. Nunca f-string em query.
- **Rate limiting** nos endpoints de login e upload (`slowapi` ou Azure API Management). Sem isso, força bruta é gratuita.
- **Upload**: valide tipo (415) e tamanho (413); gere nome novo com `uuid4` — nome vindo do cliente abre path traversal e sobrescrita
- **Dependências**: `pip-audit` ou Dependabot no repositório. Biblioteca desatualizada é o vetor mais barato de explorar.
- **Erro nunca vaza stack trace** para o cliente. Log detalhado no servidor, mensagem genérica na resposta.

## 5. Observabilidade

Sem instrumentação você descobre o problema pelo cliente reclamando.

```bash
az monitor app-insights component create -g rg-projeto4 \
  --app ai-projeto4 -l brazilsouth --application-type web

az webapp config appsettings set -g rg-projeto4 -n <app> \
  --settings APPLICATIONINSIGHTS_CONNECTION_STRING="<connection-string>"
```

```python
# instrumentação automática: request, dependência (SQL, HTTP), exceção e log
from azure.monitor.opentelemetry import configure_azure_monitor
configure_azure_monitor()
```

### Os três pilares

| Pilar | Responde | Onde |
|---|---|---|
| **Logs** | O que aconteceu naquela requisição | `logging` do Python → App Insights |
| **Métricas** | Como o sistema está agora | Requests/s, latência p95, taxa de erro |
| **Tracing** | Onde o tempo foi gasto | Distributed tracing entre API e banco |

### Logging estruturado

Logue o que ajuda a investigar: rota, status, duração, id da requisição, id do usuário. **Nunca** senha, token, CPF ou conteúdo de arquivo.

```python
logger.info("item_criado", extra={"item_id": item.id, "usuario_id": user.id})
```

Nível certo: `INFO` para evento de negócio, `WARNING` para o que degrada, `ERROR` para o que falhou. `DEBUG` ligado em produção enche o App Insights e custa dinheiro.

## 6. Alertas

Alerta que ninguém lê é ruído; alerta que falta é incidente descoberto tarde. Comece com quatro:

| Alerta | Condição | Por quê |
|---|---|---|
| Disponibilidade | `/health` falhando 3x seguidas | A app caiu |
| Taxa de erro | 5xx > 5% em 5 min | Algo quebrou no último deploy |
| Latência | p95 > 2s por 10 min | Bate no RNF01 |
| Custo | Gasto > 80% do orçamento | Crédito de estudante acaba silencioso |

O alerta de disponibilidade vale mais que todos os outros juntos.

## 7. Custo (FinOps mínimo)

Free tier tem 60 min de CPU/dia. App Insights cobra por volume ingerido — `DEBUG` em produção é a forma mais fácil de queimar crédito.

- Alerta de orçamento no **primeiro dia**
- Sampling no App Insights se o volume crescer
- Desligue recurso de teste que ninguém usa
- `az consumption budget` ou Cost Management no portal

## Checklist da fase de Qualidade

**Segredos**
- [ ] Nenhum segredo no histórico do Git (conferido com `git log -p`)
- [ ] Segredos sensíveis no Key Vault, referenciados por App Setting
- [ ] Managed identity onde for possível, no lugar de connection string

**Autenticação**
- [ ] Senha com hash forte (bcrypt/argon2)
- [ ] JWT com expiração curta; segredo no Key Vault
- [ ] Autorização checada em cada endpoint com id (sem IDOR)
- [ ] Erro de login genérico

**Aplicação**
- [ ] HTTPS only ligado
- [ ] CORS restrito ao domínio do front
- [ ] Rate limiting em login e upload
- [ ] Upload valida tipo e tamanho e gera nome novo
- [ ] Dependências auditadas
- [ ] Stack trace não aparece na resposta

**LGPD**
- [ ] Base legal documentada
- [ ] Só coleta o que usa
- [ ] Caminho de exclusão implementado
- [ ] Nenhum dado pessoal em log

**Observabilidade**
- [ ] App Insights conectado e recebendo telemetria
- [ ] Log estruturado, sem dado sensível
- [ ] Os 4 alertas configurados com destinatário real
- [ ] Alerta de orçamento ativo
