# Pesquisa técnica — Dionísio (CRM de reservas)

> Pesquisa complementar ao customer discovery, feita fora da conversa direta com o cliente. Sistema citado na Conversa 1, mas **fora das hipóteses priorizadas (H1–H4)** — ver [`00-customer-discovery.md`](../00-customer-discovery.md).

**Data da pesquisa:** 13/09/2026

## Pergunta a responder

O Dionísio (sistema de reservas/CRM citado pelo cliente: "a gente está com aquele do Dionísio lá, que é um pouco de AI") tem API para integração?

**Contexto de prioridade:** o próprio cliente disse, na Conversa 1, que esse lado "a gente já está tocando bem" — ou seja, não é uma dor identificada, e não gerou hipótese (H1–H4). Esta pesquisa existe só para completar o mapa de sistemas do cliente, não porque o projeto pretenda integrar com ele agora.

## O que é

**Dionísio** (`odionisio.com`) — plataforma de "inteligência operacional" para restaurantes: uma IA atende o WhatsApp do restaurante (reservas, pedidos, dúvidas), registra cada interação como dado de CRM, confirma reservas automaticamente, reduz no-show (até 40%, segundo o próprio site) e dispara campanhas de reativação de clientes.

## O que encontramos

- **Não encontramos API pública nem portal de desenvolvedor.** O site não menciona documentação técnica, chave de API self-service, nem SDK.
- O produto se descreve como conectável a "ferramentas que você já usa" — citando PDVs como Saipos, Nuvy e Atena, além de iFood e outros apps de delivery — mas **não cita Everest ou Colibri especificamente**, os sistemas que o Grupo Saints realmente usa.
- Existe um subdomínio de aplicação (`app.odionisio.com`, com termos de uso próprios — "Dionisio CRM"), indicando um produto SaaS ativo, mas nada de documentação de integração aberta.
- Há menção a exportação de dados no contexto de LGPD (direito do titular a exportar/cancelar dados), o que é uma garantia de compliance, não uma API para sistemas de terceiros.

## Implicações para o escopo

1. Sem evidência de API pública — qualquer integração futura provavelmente dependeria de contato comercial direto com a Dionísio, como parece ser padrão nesse mercado (mesmo perfil do Colibri).
2. **Baixíssima prioridade agora**: o cliente não identificou dor nessa área; investir tempo de pesquisa ou negociação de acesso aqui não se justifica enquanto H1 e H2 (as prioridades reais) não estiverem endereçadas.
3. Só revisitar esta pesquisa se, numa conversa futura, a reserva/CRM entrar como novo requisito no MoSCoW — o que hoje não há evidência de discovery para sustentar.

## Fontes

- https://www.odionisio.com/
