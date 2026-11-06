# Anexos de imagem — RF09

> Planejamento criado em 06/11/2026, revisado no mesmo dia. **Nada implementado.**
>
> Usa o Blob Storage para o que ele existe — guardar binário de usuário — com a
> regra de que **a foto precisa ter função**. Foto decorativa gera a pergunta "e
> o que ela faz?", e aí o Blob volta a parecer enfeite de currículo.

| | A foto é… | Resolve |
|---|---|---|
| **RF09** — nota fiscal anexada ao custo do período | **prova** | O número do fechamento não tem documento atrás |
| ~~RF10 — produto com foto como âncora de identidade~~ | — | **Retirado.** Ver "O que foi retirado" abaixo |

**RF09 é Must**, por decisão de 06/11/2026. É uma **aposta de produto
deliberada**, não um requisito validado: a Persona 3 não foi entrevistada e o
cliente parou de responder. Com o prazo curto e o vácuo deixado pelo cliente,
esperar validação é paralisia — a escolha foi apostar e dizer que é aposta.

---

## Pré-requisito comum: recuperação autorizada

Planilha você só guarda. Imagem você tem que **exibir** — e hoje isso não é
possível: `UploadCusto.url` guarda a URL nua do blob, que devolve **401** sem
SAS, porque o container é (corretamente) privado.

Por isso o item 5 da fila de `09-uso-da-nuvem.md` deixa de ser melhoria e passa
a ser **bloqueador**: sem um caminho de download autorizado, nenhuma das duas
funcionalidades funciona.

```
GET /api/v1/anexos/{id}/conteudo
  → 302 para uma URL com SAS de leitura, escopo de um blob, validade de minutos
```

Decisões que valem ser explícitas:

- **SAS de leitura, um blob, TTL curto** (sugestão: 5 min). Credencial com o menor escopo e o menor tempo que resolvem o problema.
- **302 em vez de proxy.** Fazer a API baixar e repassar o arquivo gastaria CPU e memória da instância B1 em cada visualização. O redirecionamento deixa o download entre o navegador e o Storage.
- O `url` atual em `UploadCusto` passa a ser tratado como **localizador interno**, não como link. Candidato a sair do schema de resposta, que hoje expõe um campo que não funciona.

---

## O que imagem muda, e planilha não exigia

Esta seção existe porque cada item aqui é uma decisão que precisa estar tomada
**antes** de escrever código, não descoberta depois.

| Risco | Por que aparece agora | Decisão |
|---|---|---|
| **Tipo falsificado** | Hoje o upload aceita `.xlsx` e, se o conteúdo não for planilha, o *tradutor* rejeita — existe uma segunda checagem implícita. Com imagem essa rede desaparece | Validar **magic bytes**: JPEG (`FF D8 FF`), PNG (`89 50 4E 47`), PDF (`%PDF`). Extensão e `Content-Type` do cliente não são prova |
| **XSS armazenado** | SVG é XML executável. Servido na origem da aplicação, vira script rodando no contexto do usuário | **Recusar SVG.** E servir pelo domínio do Storage com SAS, nunca pela origem da API |
| **EXIF** | Foto de celular carrega GPS, modelo do aparelho e horário. Nota fotografada por um funcionário vira metadado de **localização de uma pessoa** — toca o RNF03 e a LGPD | Remover EXIF no upload, antes de gravar. Exige uma biblioteca de imagem (Pillow) — dependência nova, a registrar |
| **Tamanho e memória** | `max_upload_mb = 10` e foto de celular tem 3–8 MB: uma foto quase estoura o limite. Pior, `await arquivo.read()` carrega o arquivo **inteiro na memória** de uma instância B1 | Reduzir a imagem no cliente antes de enviar, e tratar o limite como decisão consciente. Múltiplas fotos por requisição estão fora de escopo |
| **Perda irreversível** | Planilha o cliente reexporta do ERP. Nota fiscal fotografada, não | `soft delete` no Blob (item 3 da fila) antes de aceitar o primeiro anexo |

---

## RF09 — Nota fiscal anexada ao custo do período

### Valor

O fechamento acusa que o custo divergiu. A pergunta imediata do dono é "por
quê?", e a resposta está num documento. Hoje o sistema produz o número e para
ali.

> Fluxo: fechamento mostra divergência em ALIMENTOS → abre o período → vê as
> notas daquele mês → acha a do fornecedor que subiu o preço.

Quem fotografa é quem **recebe a mercadoria**, no momento em que recebe — não é
trabalho novo inventado, é o papel que já existe. E é genérico: todo negócio tem
nota.

**Fraqueza honesta:** sem OCR, o anexo *acompanha* dado, não *produz* dado. O
valor é trilha de auditoria e contexto, não automação. Dizer isso é melhor que
deixar alguém supor que o sistema lê a nota.

### Modelo

Tabela nova, **não** reaproveitar `UploadCusto`:

| Motivo | |
|---|---|
| Cardinalidade | `UploadCusto` é um por (casa, período, tipo); nota fiscal são várias por período |
| Extração | `UploadCusto` gera `LinhaCusto`; anexo não gera nada |
| Ciclo de vida | Reenviar um export **substitui**; anexar outra nota **acumula** |

```
Anexo
  id
  casa_id        FK casas
  periodo        AAAA-MM
  tipo           "nota_fiscal" | "outro"
  descricao      texto livre, opcional (ex.: "Fornecedor X, nota 1234")
  nome_original  nome enviado, só como metadado
  blob_name      uuid4, único
  content_type
  tamanho_bytes
  criado_em
```

### Endpoints

| Método | Rota | Status |
|---|---|---|
| POST | `/api/v1/casas/{casa_id}/anexos` | **201** · 404 casa · 413 tamanho · 415 tipo · 422 conteúdo inválido |
| GET | `/api/v1/casas/{casa_id}/anexos?periodo=` | 200, paginado |
| GET | `/api/v1/anexos/{id}/conteudo` | **302** para o SAS · 404 |
| DELETE | `/api/v1/anexos/{id}` | **204** · 404 |

### Tela

Seção "Documentos do mês" na tela de Fechamento, com miniaturas. Clique abre
pelo SAS. Fica ao lado do número que o documento justifica — e não numa aba
separada, que ninguém visitaria.

---

## O que foi retirado, e por quê

A primeira versão deste documento especificava um **RF10 — cadastro de produto
com foto como âncora de identidade**: um cadastro canônico com tabela de aliases
mapeando as strings de nome que vêm do export, e a foto servindo de âncora
visual para a pessoa decidir se dois nomes são o mesmo produto.

**Retirado no mesmo dia.** O motivo fica aqui porque a decisão é mais útil que a
proposta:

- **A foto não fazia o trabalho de identidade.** O mapeamento de aliases fazia. A
  foto era auxílio visual à interface do mapeamento — o recurso funcionaria igual
  sem foto nenhuma. Na prática, duas coisas separadas foram amarradas: um defeito
  real de qualidade de dado e a vontade de usar o Blob com imagem. A amarração
  fez a foto *parecer* propositada.
- **Dificultava o resto do sistema.** Agrupar por produto canônico muda a chave de
  agregação de `top-itens`, `historico_itens` e da recomendação de compra. Como
  os números da casa piloto estão conferidos contra produção, seria preciso
  manter **dois caminhos de agregação para sempre** (com e sem alias) só para não
  quebrá-los.
- **Exigia curadoria manual recorrente**, sem a qual a funcionalidade não produz
  nada.

O problema que ela tentava resolver **é real** e não foi descartado com ela — foi
movido para onde pertence: `01-requisitos.md`, seção 1.9, como risco conhecido de
qualidade de dado. Resolvê-lo não depende de foto.

### Se você quiser uma segunda funcionalidade de imagem

A candidata honesta é **registro de perda/quebra com foto**, porque ali a foto é
*primária*: "jogamos 4 kg de queijo fora" com foto é uma afirmação diferente de
sem foto — a imagem é a prova, não um auxílio. É aditiva (tabela nova, endpoint
novo) e só toca o cálculo se for ligada à decomposição do ajuste, o que pode ser
um passo separado e posterior.

Não está especificada aqui porque não foi decidida.

---

## Ordem de implementação

1. Fila nível 1 de `09-uso-da-nuvem.md` — em especial **`soft delete` no Blob**
   (`infra/ajustes-nivel-1.sh`)
2. **Endpoint de download com SAS** (item 5 da fila) — bloqueador
3. Validação de imagem: magic bytes, recusa de SVG, remoção de EXIF
4. **RF09**: modelo, endpoints, tela

## Referências

- Auditoria e fila de ajustes de nuvem: `09-uso-da-nuvem.md`
- Requisitos, personas e MoSCoW: `01-requisitos.md`
- Regra do cálculo de CMV e os tradutores: `07-fechamento-cmv.md`
