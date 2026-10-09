# Pesquisa técnica — Colibri (NCR Colibri)

> Pesquisa complementar ao customer discovery, feita fora da conversa direta com o cliente — checagem de viabilidade técnica antes de comprometer o escopo. Ligada à **H3** (previsão de compra a partir do histórico de vendas) em [`00-customer-discovery.md`](../00-customer-discovery.md).

**Data da pesquisa:** 13/09/2026

## Pergunta a responder

O Colibri (sistema de vendas/PDV citado pelo cliente, integrado à maquininha e ao Everest, com ~16 anos de histórico) tem API própria para extrair dados de vendas, ou o histórico só é acessível através do Everest?

## O que é

**Colibri**, hoje sob a marca **NCR Colibri** — PDV líder para food service no Brasil, com mais de 15 mil pontos de venda instalados. Foi comprado pela **RS Solutions** (dona do POS Fácil) em parceria com a NCR (americana). Bate com a descrição do cliente ("sistema de vendas que é integrado com a Maquininha e com o Everest").

## O que encontramos

- Tem **API REST** própria — descrita como voltada a "serviços operacionais" do Colibri: consultar mesas, comandas, clientes, lançar pedidos e pagar contas (leitura e escrita no banco do Colibri).
- Tem um **SDK** para parceiros construírem extensões/plugins, distribuídos por um **Marketplace** (`marketplace.ncrcolibri.com.br`) — mesmo modelo usado por integrações conhecidas (PagSeguro, Rede, Cielo, iFood, Rappi).
- **Diferença importante em relação ao Everest:** não encontramos um ambiente de homologação público e auto-atendível. Os domínios técnicos citados (`api-master.ncrcolibri.com.br`, `wiki.ncrcolibri.com.br`) não resolveram no acesso externo — consistente com a própria página do Colibri, que diz que integrações próprias acontecem "através de projeto, onde a Colibri Sistemas faz a validação". Ou seja, o acesso parece **mediado por parceria/projeto aprovado**, não self-service.
- **Achado que reduz a urgência dessa API para o projeto:** o próprio cliente descreveu, na Conversa 1, que o Colibri já alimenta o Everest automaticamente ("o Colibri passou pro Everest que vendeu dois aperóis"). Ou seja, o histórico de vendas necessário para H3 (previsão de compra) **provavelmente já está acessível dentro do Everest**, sem precisar de acesso direto à API do Colibri.

## Implicações para o escopo

1. Não é necessário tratar o acesso à API do Colibri como bloqueante — os dados de vendas relevantes (para H3) já chegam ao Everest pela integração nativa que o próprio grupo já usa.
2. Se, no futuro, for preciso um dado que só existe no Colibri (ex.: granularidade de item por comanda em tempo real), o caminho é mais lento do que o do Everest: provavelmente exige que o cliente (Grupo Saints) abra um pedido de integração com a NCR/Colibri Sistemas, não uma credencial obtida rapidamente.
3. Prioridade de investigação: baixa por ora. Só vale aprofundar se H3 avançar no MoSCoW e a granularidade de dados do Everest se mostrar insuficiente.

## Perguntas para a próxima conversa com o cliente

- Confirmar com a Joyce/Renata/Wellington: os dados de vendas que aparecem no Everest têm o mesmo nível de detalhe do Colibri, ou é um resumo?
- O grupo já tem algum tipo de relação de parceria/integração formal com a NCR Colibri, ou só usa o sistema como cliente final?

## Fontes

- https://colibri.com.br/
- https://colibri.com.br/solucoes
- https://startups.com.br/negocios/em-nova-fase-colibri-quer-se-tornar-a-square-brasileira/
- https://donuz.com.br/blog/docs/integracao-ncr-colibri/
- (domínios técnicos citados em buscas, não resolvidos externamente): `api-master.ncrcolibri.com.br`, `wiki.ncrcolibri.com.br`, `marketplace.ncrcolibri.com.br`
