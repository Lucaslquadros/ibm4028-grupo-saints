# Pesquisa técnica — Everest (ACOM Sistemas)

> Pesquisa complementar ao customer discovery, feita fora da conversa direta com o cliente — checagem de viabilidade técnica antes de comprometer o escopo. Ligada à **H1** em [`00-customer-discovery.md`](../00-customer-discovery.md).

**Data da pesquisa:** 13/09/2026

## Pergunta a responder

O Everest (ERP citado pelo cliente na Conversa 1 para financeiro, compras e estoque) tem API para extrair dados programaticamente, ou o único caminho é o export manual de Excel que a Joyce e a Renata já fazem hoje?

Isso decide se **H1** (dashboard de delta custo teórico × custo real) pode ser alimentado por integração automática ou depende de upload manual.

## O que é

**Everest 3.0**, da **ACOM Sistemas** — ERP de food service com módulos financeiro, compras, estoque e administrativo. Bate com a descrição do cliente na Conversa 1 ("cadastram o filé mignon... tem o modo financeiro, modo vendas, modo compras").

## O que encontramos

- Tem **API REST documentada**, com especificação Swagger (`swagger.json`) e um ambiente de homologação em `homologacao.acomsistemas.com.br/api`. Ou seja, a ACOM oferece integração programática — não é um sistema fechado.
- O Everest tem um módulo de **BI nativo, o Ever.BI**, com submódulos Financeiro, Compras e Vendas, que já promete "transformar informação em relatórios inteligentes". Isso pode **sobrepor** parte do que o projeto pretende resolver.
- Não encontramos: preço, prazo de liberação de credencial, nem se o acesso à API depende do plano contratado especificamente pelo Grupo Saints (o cliente).
- A integração divulgada publicamente é majoritariamente para *receber* dados de PDVs (mais de 80 parceiros de frente de caixa) — não achamos confirmação pública de que exportar dados *para fora* via API é liberado por padrão a qualquer cliente.

## Implicações para o escopo

1. Integração via API é **tecnicamente viável** — o MVP não precisa ser desenhado só em torno de upload manual.
2. Mas login de usuário no Everest **não é o mesmo** que credencial de API — precisa confirmar com o cliente e/ou a ACOM se a API está habilitada no contrato do Grupo Saints.
3. Risco de sobreposição com o **Ever.BI**: se ele já cruza custo teórico × real, a proposta de valor do projeto precisa ser outra (ex.: visão cross-casas em tempo real, alertas automáticos, camada de previsão de compra — H3). Perguntar ao cliente se ele conhece/usa o Ever.BI é obrigatório antes de desenhar a solução.
4. **Plano de contingência:** a disciplina exige pelo menos 1 upload no MVP. Então o fluxo pode nascer com upload manual do export (o mesmo Excel que a Joyce já tira hoje) alimentando o dashboard, e evoluir para API se ela for liberada a tempo — isso tira a dependência da API do caminho crítico do cronograma de 14 semanas.

## Perguntas para a próxima conversa com o cliente

- A API do Everest está habilitada no contrato de vocês com a ACOM? Dá para pedir uma credencial de homologação?
- Vocês conhecem/usam o Ever.BI? Ele já mostra o delta custo teórico × real, ou fica só nos relatórios brutos que a Joyce hoje monta na mão?

## Fontes

- https://everestfood.com.br/
- https://everestfood.com.br/everest/
- https://everestfood.com.br/everbi-relatorios-inteligentes-da-acom-sistemas/
- https://acomsistemas.com.br/blog/relatorios-avancados/
- https://homologacao.acomsistemas.com.br/docs/
- https://acomsistemas.com.br/
