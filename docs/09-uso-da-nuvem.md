# Uso dos recursos de nuvem — auditoria e fila de ajustes

> Criado em 06/11/2026. Responde a duas perguntas: **como cada recurso do Azure
> está sendo usado hoje** e **em que ordem corrigir o que está mal usado**.
>
> O critério é "recurso escolhido é recurso bem usado". Acrescentar serviço para
> encher lista é pior que não acrescentar: "por que vocês usaram Redis?" é uma
> pergunta ruim de responder, e "por que vocês *não* usaram" é ótima.

Os dados desta auditoria vieram da subscription real (`az ... show`), não da
intenção do projeto. Onde a configuração contradiz o que o código ou o
documento de requisitos afirma, isso está dito.

> **Como ler este documento.** A seção 2 descreve o estado em que a auditoria
> **encontrou** cada recurso, preservado de propósito — é o diagnóstico. O que
> já foi corrigido está marcado com ✅ e consolidado na **seção 1b**.

---

## 1. O achado principal — e o que ele rendeu

**Estado em que a auditoria encontrou a configuração:**

```
appLogs: Off   |   httpLogs: false   |   detailedErrors: false
Application Insights: nenhum componente na subscription
```

A regra 9 do projeto é "stack trace vai para o log, nunca para a resposta HTTP",
e `app/main.py` a cumpre: o handler de exceção registra `logger.exception(...)` e
devolve um 500 genérico. **Só que não existia destino de log configurado** — os
stack traces iam para o nada.

A consequência não era teórica. O 500 do `GET /api/v1/uploads-custo`
(incompatibilidade de `GROUP BY` com o Azure SQL) rodou em produção sem ninguém
perceber, e foi diagnosticado **lendo código**, não lendo log, porque não havia
log para ler.

**Corrigido em 06/11/2026** (`infra/ajustes-nivel-1.sh`). Minutos depois, o log
já entregava a causa exata, com a mensagem literal do SQL Server:

```
ERROR [projeto4] Erro não tratado em GET /api/v1/uploads-custo
pyodbc.ProgrammingError: ('42000', "[ODBC Driver 18 for SQL Server][SQL Server]
Column 'uploads_custo.casa_id' is invalid in the select list because it is not
contained in either an aggregate function or the GROUP BY clause")
```

É o exemplo mais limpo de recurso mal usado no projeto: não faltava serviço,
faltava configuração — e ligar o log do App Service é um comando, com custo zero.
Vale levar esse trecho para a apresentação: ele prova a regra 9 funcionando
(stack trace no log, 500 genérico para o cliente) e explica por que
`tests/test_dialeto_sql.py` existe.

## 1b. Estado atual da configuração (06/11/2026)

A auditoria da seção 2 descreve o que foi **encontrado**. Isto é o que está
valendo agora:

| Ajuste | Antes | Depois |
|---|---|---|
| Always On | `false` | **`true`** — fim do cold start de 30–60s |
| Log de aplicação | `Off` | **`Information`** |
| Log de HTTP + erro detalhado | `false` | **`true`** |
| Soft delete no Blob (blob e container) | desligado | **14 dias** |
| `httpsOnly` | já era `true` | confirmado — `http://` devolve 301 |
| Credencial federada OIDC | só formato por nome | **+ formato de subject imutável** (ver `06-guia-deploy-azure.md`, Atenção 4b) |
| Verificação pós-deploy | só `"status":"ok"` | **compara o SHA publicado** (Atenção 6) |

Com isso, **o deploy automático passou a funcionar pela primeira vez** — até
06/11/2026 todas as publicações tinham sido manuais, e a falha do pipeline
passava despercebida porque ninguém abria o run.

---

## 2. Auditoria por recurso

### App Service — `plan-projeto4` (B1 Basic) + `app-projeto4-saints2026`

**Papel:** hospedar a API FastAPI.

| Bem usado | Mal usado |
|---|---|
| `/health` registrado como *health check path* — é o que o App Service usa para decidir reiniciar a instância | ✅ *(corrigido)* `alwaysOn: false`, num plano que **suporta** Always On. A instância dormia em ~20 min e a primeira requisição levava 30–60s |
| `gunicorn -w 2 -k uvicorn.workers.UvicornWorker` — servidor de produção, não `fastapi dev` | _(ver nota de correção abaixo sobre `httpsOnly`)_ |
| Deploy por código (Oryx) com `SCM_DO_BUILD_DURING_DEPLOYMENT`, coerente com o stack escolhido | ✅ *(corrigido)* Todos os logs desligados — ver seção 1 |
| | Sem identidade gerenciada: o acesso a Blob e SQL usa segredo em App Setting |
| | `criar_tabelas()` no startup em vez de migração versionada — DDL implícito a cada boot, e ainda pesa no cold start |

>#### Nota de correção (06/11/2026)
>
> A primeira versão desta auditoria listava **`httpsOnly` não forçado** como
> pendência. Estava **errado**: o campo `httpsOnly` não existe em
> `az webapp config show` — ele vive em `az webapp show` —, e consultá-lo no
> comando errado devolve `null`, que foi lido como "desligado".
>
> Na verdade `infra/provisionar.sh:118` já executa
> `az webapp update --https-only true` desde o provisionamento, e o valor
> confirmado é `true`. O RNF03 estava cumprido nesse ponto.
>
> Fica registrado porque auditoria que não admite o próprio erro não serve como
> auditoria — e porque a lição é concreta: **conferir em qual comando o campo
> mora antes de concluir que ele está ausente.**

### Azure SQL — `sql-projeto4-saints2026` / banco `projeto4` (Basic, 2 GB)

**Papel:** dado estruturado — casas, uploads e linhas de custo.

| Bem usado | Mal usado |
|---|---|
| **Agregação no banco** (`SUM`/`GROUP BY` em `app/crud.py`), nunca em Python. É o uso correto de um relacional e a razão de a instância B1 aguentar 345 itens × 24 meses | Sem administrador do Entra ID: só autenticação SQL, com senha em App Setting |
| Modelagem relacional **justificada**: o fechamento literalmente é um join entre dois uploads do mesmo período | Firewall com a regra "permitir serviços do Azure" (`0.0.0.0`), mais ampla do que o necessário |
| Paginação em toda listagem; índices nas colunas de filtro (`casa_id`, `periodo`, `tipo`, `nivel`, `grupo`) | Backup com redundância `Local`, sem redundância de zona |
| TLS mínimo 1.2 | Sem migração versionada (ver App Service) |

> **Sobre o firewall:** estreitá-lo de verdade exigiria integração com VNet e
> private endpoint, que o tier atual não sustenta — e subir de tier consome
> crédito que o projeto não tem. Fica documentado como limitação consciente, não
> como descuido.

### Blob Storage — `stprojeto4saints2026` (StorageV2, Standard_LRS, Hot)

**Papel:** guardar o arquivo original de cada upload.

| Bem usado | Mal usado |
|---|---|
| Container **privado**: `allowBlobPublicAccess: false`, `publicAccess: null`. As planilhas do cliente não são baixáveis publicamente | ✅ *(corrigido — 14 dias)* **`soft delete` desligado.** Substituir um upload apagava o original do cliente para sempre |
| Nome de blob gerado com `uuid4`, nunca o nome enviado pelo cliente — regra 10 do projeto, e defesa contra path traversal e colisão | Sem versionamento e sem regra de ciclo de vida (tudo permanece em Hot indefinidamente) |
| Binário no object storage, ponteiro no banco — o padrão cloud, em vez de BLOB em tabela | Autenticação por connection string (shared key) em vez de identidade gerenciada |
| Blob antigo é removido quando o upload é substituído | **A URL guardada em `UploadCusto.url` não serve para nada**: é a URL nua do blob e devolve 401 sem SAS. Na prática o Blob é hoje *somente escrita* |
| TLS mínimo 1.2 | |

### Static Web App — `swa-projeto4-saints2026` (Free)

**Papel:** hospedar o frontend React.

Usado para exatamente o que serve: CDN, certificado e build próprio por GitHub
Actions, desacoplado do backend. **Sem reparo.**

A *managed API* do SWA está deliberadamente sem uso — o backend é o App Service,
e duplicar isso criaria dois lugares servindo a mesma API. A autenticação
embutida do SWA também não resolve o RNF03: ela protege o frontend, não a API,
que é um recurso separado e continuaria pública.

### GitHub Actions + identidade `id-gh-ibm4028`

**Papel:** CI/CD.

**O recurso melhor usado do stack** — este você defende sem ressalva:

- **OIDC federado**: nenhum segredo de longa duração guardado no GitHub
- Testes como **portão** do deploy (`needs: [testes]`), não como etapa paralela
- Verificação de `/health` **depois** de publicar — deploy sem verificação é deploy que o cliente descobre quebrado
- `concurrency` configurado: dois merges seguidos não deployam um por cima do outro

### Docker / ACR

**Papel declarado no documento de requisitos:** containerização.

**Papel real: nenhum.** O `Dockerfile` existe, mas **não há ACR na
subscription** e o deploy é por código.

**Decidido (registrado em `01-requisitos.md` §8):** o `Dockerfile` é
apresentado como "preparado para conteinerizar, não usado neste deploy". Na
apresentação, dizer isso antes de perguntarem.

---

## 3. Fila de ajustes, por valor

Ordenada por **risco removido ÷ esforço**, não por elegância. A regra prática:
não comece o nível seguinte antes de fechar o anterior.

### Nível 1 — ✅ **aplicado em 06/11/2026**

São comandos `az`, nenhum exige mexer em código — `infra/ajustes-nivel-1.sh`
executa os três e confere cada propriedade no fim. Eram quatro na primeira
versão; o quarto (`httpsOnly`) saiu por já estar aplicado.

| # | Ajuste | Por que primeiro |
|---|---|---|
| 1 | **Always On** no App Service | Remove o modo de falha mais provável da apresentação: avaliador abre o link, espera um minuto, conclui que está quebrado. Melhor relação valor/esforço de toda a lista |
| 2 | **Ligar os logs** do App Service (aplicação + HTTP) | Transforma a regra 9 de intenção em fato. Sem isto você está cego em produção — e já esteve, no 500 do `uploads-custo` |
| 3 | **`soft delete` no Blob** (7–30 dias) | Protege arquivo de cliente que não pode ser reexportado. Vira **obrigatório** antes de qualquer anexo de imagem: planilha o cliente reexporta, nota fiscal fotografada não |
| ~~4~~ | ~~`httpsOnly: true`~~ | **Removido da fila:** já está `true` desde o provisionamento. Entrou por erro de consulta — ver nota de correção |

### Nível 2 — destrava o resto

| # | Ajuste | Por que | O que destrava |
|---|---|---|---|
| 5 | 🔄 **Endpoint de download com SAS de curta duração** — **no ciclo 07–09/11 como RF14** (`11-ciclo-explicacao-do-ajuste.md` §4b) | Hoje o Blob é somente escrita. Além de consertar isso, demonstra *least privilege* — credencial com escopo de um blob e validade de minutos | **Pré-requisito** do RF09 (ver `10-anexos-de-imagem.md`): imagem precisa ser exibida, não só guardada. O RF10 foi retirado em 06/11 |
| 6 | ⬜ **Application Insights** | A única forma de ver requisição, falha, latência e dependência ao longo do tempo. Está como "extra valorizado" não marcado no documento de requisitos e cobre a fase de Qualidade, que não foi entregue | Diagnóstico de qualquer coisa futura |

### Nível 3 — postura de segurança

Mais trabalho, alta defensibilidade. Faça na ordem: a identidade gerenciada
reduz o que sobra para o Key Vault guardar.

| # | Ajuste | Por que |
|---|---|---|
| 7 | **Identidade gerenciada do App Service → Blob** | Elimina a connection string de shared key. Credencial que não existe não vaza |
| 8 | **Key Vault** para o que continuar sendo segredo (`DATABASE_URL`) | Rotação e auditoria de acesso ao segredo, em vez de App Setting em texto |
| 9 | **Administrador Entra ID no SQL** | Reduz a dependência de senha; permite autenticação por identidade também no banco |

### Nível 4 — engenharia estrutural

| # | Ajuste | Por que |
|---|---|---|
| 10 | **Migração versionada (Alembic)** em vez de `criar_tabelas()` no startup | DDL implícito a cada boot é risco em produção e custo no cold start. É o ajuste de maior valor técnico e o de maior esforço — por isso vem por último, não por ser menos importante |

### Decidido não fazer, com motivo

Registrar a recusa vale tanto quanto registrar a adoção.

| Recurso | Por que não |
|---|---|
| **Redis Cache** | 10–15 usuários internos, uso concentrado no fechamento mensal. Não há nada a cachear, e "por que vocês cachearam?" não tem resposta boa |
| **API Management** | Uma API, um consumidor. Over-engineering visível |
| **Private endpoint / integração VNet** | Exigiria tier superior de App Service e SQL. O crédito Azure for Students não sustenta, e o ganho num projeto de faculdade com dado já anonimizado não justifica |
| **Redundância de zona no backup** | Indisponível no tier Basic |
| **Ciclo de vida Hot → Cool no Blob** | Volume de dados irrelevante; a economia seria de centavos |
| **Azure Functions** | Só entraria se houvesse algo a agendar. Se o alerta de variação de custo por item (Could) for implementado, reavaliar |

---

## 4. Como isso entra na apresentação

Dois recursos bem justificados valem mais que cinco na lista. O argumento forte
não é "usamos sete serviços do Azure", é:

> Cada recurso está aqui por um motivo que a gente sabe dizer, e os que **não**
> estão também — Redis e API Management foram recusados por escrito, com o
> motivo.

E o argumento mais honesto, que vale mais que qualquer um deles:

> Auditamos a própria configuração contra o que o nosso documento afirmava, e
> achamos quatro distâncias entre os dois. Está tudo em `docs/09-uso-da-nuvem.md`,
> com a ordem de correção.

---

## Referências

- Especificação dos anexos de imagem (RF09; RF10 retirado): `10-anexos-de-imagem.md`
- Ciclo 07–09/11 (RF14 = item 5 desta fila): `11-ciclo-explicacao-do-ajuste.md`
- Requisitos, limitações conhecidas e MoSCoW: `01-requisitos.md`
- Passo a passo de deploy e provisionamento: `06-guia-deploy-azure.md`
- Roteiro da demonstração: `08-roteiro-demo.md`
