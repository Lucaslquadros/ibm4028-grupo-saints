# Plano de Sprints — Retomada do Projeto

**IBM4028 — Projeto 4 | IBMEC CDIA 2026.2**

> Criado em 09/10/2026, na retomada do projeto após o período sem desenvolvimento
> de domínio. Ver `docs/01-requisitos.md` (histórico de mudanças, v0.3) para o que
> mudou nos requisitos nesta mesma retomada.

---

## Diagnóstico no momento da retomada (09/10/2026)

| Frente | Estado |
|---|---|
| Discovery / requisitos | Conversa 1 (cliente/sócio) validou o Problema 1 (custo/compras — RF01/RF02/RF04) e o Problema 2 (RH/escala — RF03/RF05, ainda hipótese). **Conversa 2 (Joyce, Renata, Wellington) ainda não aconteceu.** |
| Código | Esqueleto FastAPI funcionando, 30 testes verdes, mas domínio **ainda é o placeholder `Item`/`Arquivo`**. Nenhuma entidade real do projeto existia até esta retomada. |
| Deploy | Nunca aconteceu. `AZURE_WEBAPP_NAME` no workflow ainda estava com o valor placeholder `TROCAR`. |
| Processo | Não havia repositório Git nem board — criados nesta retomada: [`Lucaslquadros/ibm4028-grupo-saints`](https://github.com/Lucaslquadros/ibm4028-grupo-saints), board "IBM4028 - Grupo Saints" (colunas Backlog/To Do/In Progress/Review/Done). |

**Prazo:** hoje é 09/10/2026, o MVP (1 CRUD + 1 upload + 1 dashboard no ar) vence em
**09/11/2026** — 4 semanas, o espaço de exatamente 2 sprints de 2 semanas mais um
buffer de 3 dias.

**Decisão de priorização:** a Sprint 1 e a Sprint 2 atacam só o **Problema 1**
(custo/compras — RF08, RF01, RF02, RF04), porque já foi validado diretamente pelo
cliente e é a prioridade nº1 dele. O **Problema 2** (RF03/RF05) não entra neste
ciclo de MVP — fica condicionado à Conversa 2 acontecer a tempo e, no caso de
RF03, à conversa com o RH sobre quais dados pessoais realmente precisam entrar
(LGPD). Isso evita bloquear o time esperando uma entrevista que ainda não tem
data. A Conversa 2 deve ser agendada **em paralelo** à Sprint 1, não depois dela.

---

## Sprint 1 — 12/10 a 23/10/2026

**Meta:** sair do domínio placeholder, cobrir o Problema 1 de ponta a ponta no
backend e colocar a aplicação no ar pela primeira vez.

**Scrum Master:** Pedro (conforme rotação definida na AC2).

| Issue | RF | Prioridade | O que entrega |
|---|---|---|---|
| Modelar `Casa`, `UploadCusto`, `ItemCusto` | RF08/RF01/RF02 | Must | Substitui `Item`/`Arquivo`; schemas, models, crud, migração de testes |
| CRUD de Casa | RF08 | Must | Cobre a exigência "1 CRUD completo" do MVP |
| Upload do export Everest (CSV) por casa/período | RF01 | Must | Cobre a exigência "1 upload" do MVP |
| Cálculo do delta custo teórico × real por casa | RF02 | Must | Endpoint que alimenta o dashboard da Sprint 2 |
| Primeiro deploy no Azure (App Service + SQL + Blob + Static Web App) | — | Must | Troca `AZURE_WEBAPP_NAME`, provisiona todos os recursos (incluindo o frontend), `/health` respondendo em produção. Passo a passo: `docs/06-guia-deploy-azure.md` |

**Em paralelo (não é issue de dev):** agendar e realizar a Conversa 2 com Joyce,
Renata e Wellington.

**Critério de pronto da sprint:** `/api/v1/casas`, `/api/v1/uploads-custo` e o
endpoint de delta respondem em produção (não só localmente), com testes cobrindo
caminho feliz e erro, conforme a Definition of Done da disciplina.

**Review (23/10):** demo para o cliente mostrando upload → delta funcionando,
mesmo que com dado de exemplo se o export real do Everest ainda não tiver
chegado.

---

## Sprint 2 — 26/10 a 06/11/2026

**Meta:** fechar o MVP com o dashboard consolidado, segurança básica e o
pipeline de CI/CD rodando de ponta a ponta — não deixar nada disso para a
véspera da entrega.

**Scrum Master:** Otávio (próximo na rotação).

| Issue | RF | Prioridade | O que entrega |
|---|---|---|---|
| Dashboard consolidado de CMV (frontend React) | RF04 | Must | Cobre a exigência "1 dashboard" do MVP |
| Segurança básica (autenticação simples, segredos no Key Vault/App Settings) | RNF03 | Must | Baseline mínimo de produção, já cobrindo o caso de RF03 entrar depois |
| CI/CD fim a fim (ci.yml + deploy-azure.yml com OIDC) | — | Must | Deploy automatizado, não manual, a partir desta sprint |
| DRE consolidada automática (se sobrar tempo) | RF06 | Should | O próprio cliente chamou de "muito simples de fazer" — quick win se der tempo |
| **Decisão sobre RF03** | RF03 | Must (hipótese) | Só entra no backlog se a Conversa 2 tiver validado o fluxo a tempo; senão, documentar como adiado em `docs/01-requisitos.md` com o motivo |

**Buffer 07/11 a 09/11:** ajustes finais, checklist de entrega parcial, README
atualizado com a URL do ambiente, preparação da demo final.

**Review (06/11):** demo completa do MVP para o cliente — upload, delta,
dashboard consolidado, no ar.

---

## Checklist de fim de cada sprint

Usar o checklist da skill `sprint-delivery-ibm4028`:

- [ ] Todo card em `Done` cumpre os 5 pontos da DoD
- [ ] Aplicação no ar e `/health` respondendo 200
- [ ] Demo feita para o cliente e feedback registrado como issue nova
- [ ] Retro gerou 3 ações com dono e prazo
- [ ] Backlog repriorizado com o PO
- [ ] `docs/01-requisitos.md` atualizado se algum requisito mudou

---

## Referências

- Board: [github.com/users/Lucaslquadros/projects/1](https://github.com/users/Lucaslquadros/projects/1)
- Repositório: [github.com/Lucaslquadros/ibm4028-grupo-saints](https://github.com/Lucaslquadros/ibm4028-grupo-saints)
- Requisitos: `docs/01-requisitos.md`
- Discovery: `docs/00-customer-discovery.md`
