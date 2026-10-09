# Roteiro de teste — 10 minutos

Como ver a aplicação funcionando, sem precisar entender o código antes.
São quatro formas, da mais rápida à mais visual. Faça na ordem.

---

## Preparação (uma vez só)

```powershell
uv sync --all-groups
Copy-Item .env.example .env
uv run python scripts/popular_dados.py
```

A última linha coloca 15 itens de exemplo em 4 categorias. Sem isso o dashboard nasce vazio e parece quebrado.

Depois, num terminal que você deixa aberto:

```powershell
uv run fastapi dev app/main.py
```

> Erro `command not found: fastapi`? O ambiente não está ativo. Use `uv run` na frente de tudo — é o que o `uv` resolve.

---

## Forma 1 — os testes (30 segundos, sem abrir navegador)

Num **segundo** terminal:

```powershell
uv run pytest -v
```

Você vê 28 testes com nome em português dizendo o que cada um garante:

```
test_criar_devolve_201_e_id                 PASSED
test_post_nao_e_idempotente                 PASSED
test_buscar_inexistente_devolve_404         PASSED
test_id_nao_numerico_devolve_422            PASSED
test_delete_devolve_204_sem_corpo           PASSED
test_patch_altera_somente_o_que_foi_enviado PASSED
```

**Isto é a documentação executável do comportamento.** Quando você trocar o `Item` pela entidade do seu projeto, esta lista é o seu alarme: falha exatamente no que faltou ajustar.

Teste o alarme agora — quebre de propósito. Em `app/routers/itens.py`, troque:

```python
@router.post("", status_code=status.HTTP_201_CREATED, ...)
# vira
@router.post("", status_code=status.HTTP_200_OK, ...)
```

Rode `uv run pytest` de novo:

```
FAILED test_criar_devolve_201_e_id - AssertionError: Criar recurso é 201 Created, não 200 OK
```

Desfaça a mudança. Você acabou de ver a rede de segurança pegar.

---

## Forma 2 — o `/docs` (o mais importante)

Abra <http://localhost:8000/docs>.

**Ninguém escreveu essa página.** O FastAPI leu os tipos do seu código e gerou tudo — parâmetros, formato do corpo, códigos de resposta.

Faça nesta ordem:

**a) `GET /api/v1/itens`** → *Try it out* → *Execute*.
Repare na resposta: `{total, limit, offset, items}`. Toda listagem é paginada. Chame três vezes — a resposta é idêntica e nada muda no servidor. É isso que "GET é seguro e idempotente" quer dizer na prática.

**b) `POST /api/v1/itens`** → *Try it out*. O corpo de exemplo já vem preenchido. *Execute*.
Olhe o status: **201**, não 200. E o `id` veio do servidor — você não mandou.

**c) Mande o mesmo POST de novo** e liste. Dois itens iguais, ids diferentes. **POST não é idempotente** — é o duplo clique do usuário.

**d) Agora quebre de propósito.** Um de cada vez:

| Mude para | O que acontece |
|---|---|
| `"nome": "AB"` | **422** — "String should have at least 3 characters" |
| `"quantidade": -1` | **422** — "Input should be greater than or equal to 0" |
| apague a linha do `categoria` | **422** — "Field required" |
| `"valor": "caro"` | **422** — não é número |

Agora **volte ao `app/routers/itens.py` e procure o código que faz essas checagens.**

**Não existe.** Você declarou o tipo em `app/schemas.py` e o Pydantic fez o resto — validou, recusou e ainda escreveu a mensagem apontando o campo. Se o código dentro da sua função rodou, o dado já está válido.

**e) `GET /api/v1/itens/{item_id}`** com `99999` → **404**, com mensagem. Não é 200 com `null`: devolver `null` obriga quem consome a adivinhar o que houve.

**f) Agora troque o id por `abc`** → **422**. Este é o mais interessante: você não escreveu *nada* para tratar isso. O `item_id: int` na assinatura já garantiu que `"abc"` nunca chega na sua função.

**g) `DELETE /api/v1/itens/1`** → **204 No Content**, corpo vazio. Apagou, não há o que devolver.
Chame de novo no mesmo id → **404**. O estado final é o mesmo das duas vezes — é isso que idempotência garante.

**h) `POST /api/v1/arquivos`** → escolha um CSV ou uma imagem qualquer.
Olhe o `blob_name` na resposta: **não é o nome do seu arquivo.** O servidor gerou um nome novo. Reaproveitar o nome do cliente permitiria sobrescrever arquivo alheio e abriria path traversal.
Tente mandar um `.exe` → **415**.

**i) `GET /api/v1/metricas/resumo`** → é este JSON que vira o dashboard.

Por fim, abra <http://localhost:8000/openapi.json>. É o contrato da API. É daí que o `/docs` sai — e é isso que o Postman, o gerador de cliente e o API Gateway consomem.

---

## Forma 3 — o REST Client (dentro do VS Code)

A Aula 04 pede a extensão **REST Client** instalada. Se ainda não tem: `Ctrl+Shift+X` → procure "REST Client" (autor Huachao Mao) → Install.

Abra o arquivo **`api.http`** na raiz do projeto. Acima de cada bloco aparece um `Send Request` acinzentado — clique.

Vantagem sobre o `/docs`: as requisições ficam **versionadas no Git**. O grupo inteiro tem os mesmos exemplos, incluindo os que falham de propósito. É o seu Postman, só que dentro do editor e dentro do repositório.

---

## Forma 4 — o painel visual

Dê duplo clique em **`frontend/painel-teste.html`**. Abre no navegador direto, sem npm, sem build.

Você vê:

- **os KPIs** — valor em estoque, itens cadastrados, unidades
- **o gráfico por categoria** — alimentado pelo `/api/v1/metricas/resumo`
- **a tabela** com os itens, com botão de excluir
- **o formulário** de criar
- **o log de requisições**, com o status code de cada chamada

Brinque: crie um item (**201**), exclua (**204**), e clique nos dois botões que provocam erro de propósito — **404** e **422**. Cada um aparece colorido no log.

Este painel também prova uma coisa invisível: **o CORS está configurado**. Se não estivesse, o navegador bloquearia toda chamada e o painel ficaria vazio, com erro no console (F12). O erro de CORS não vem do backend — vem do navegador.

> É um arquivo descartável, não o frontend do projeto. O React entra depois. Ele existe para você ver a API de pé antes disso.

---

## O que cada forma responde

| Forma | Responde |
|---|---|
| `pytest` | "continua funcionando depois que eu mexi?" |
| `/docs` | "o que essa API faz e o que ela devolve?" |
| `api.http` | "quero repetir a mesma chamada toda vez, versionada" |
| Painel | "dá para ver isso funcionando de ponta a ponta?" |

No dia a dia você usa `pytest` e `/docs` o tempo todo, `api.http` quando está construindo um endpoint novo, e o painel para mostrar a alguém.

---

## Reset

Quer recomeçar do zero?

```powershell
Remove-Item projeto4.db, uploads_local -Recurse -Force -ErrorAction SilentlyContinue
uv run python scripts/popular_dados.py
```

O banco local é um arquivo só (`projeto4.db`). Apagar é seguro — não tem nada de valioso ali.

---

## Se travar

| Sintoma | O que fazer |
|---|---|
| `command not found: fastapi` | Use `uv run fastapi dev app/main.py` |
| `ModuleNotFoundError: No module named 'app'` | Rode o comando **da raiz** do projeto, não de dentro de `app/` |
| `Address already in use` | Já tem servidor rodando. Feche o outro terminal, ou `--port 8001` |
| Painel vazio, nada carrega | O servidor não está no ar. Confira <http://localhost:8000/health> |
| Painel vazio **com** servidor no ar | CORS. Confira se `"null"` está em `CORS_ORIGINS` no `.env` |
| Dashboard tudo zerado | Falta o seed: `uv run python scripts/popular_dados.py` |
| `/docs` não atualiza | `Ctrl+Shift+R` para forçar recarregamento |
