---
sdd: 1
feature: STREAMING_SLO_TRANSPORT_EVALUATION
phase: explore
profile: dev
status: ready
approaches:
  - id: A
    summary: "Estender mode=slo para avaliar fatos kafka.lag e kinesis.shard com transport_key declarado, sem criar tool nova."
    tradeoffs:
      - "reutiliza CLI/MCP, regras e envelope já existentes"
      - "transport_key vira requisito explícito e não cobre métricas sem timestamp"
  - id: B
    summary: "Criar um modo novo por transporte e regras separadas para cada serviço."
    tradeoffs:
      - "separa semântica por serviço"
      - "duplica superfície, fixtures, regras e payload de contexto para o mesmo comparador"
  - id: C
    summary: "Mover avaliação para data-observability e ligar streaming por um adaptador."
    tradeoffs:
      - "poderia compartilhar SLI genérico"
      - "perde identidade de query/grupo/stream e cria uma segunda linguagem de SLO"
chosen: A
---

# STREAMING_SLO_TRANSPORT_EVALUATION — exploração

## Perfil

`dev`: a mudança é no próprio SparkForge.

## Evidência que abriu a frente

`sparkforge-aws rules lookup --category streaming_slo` mostrou que `SF-STREAM-011`
e `SF-STREAM-012` já julgam `streaming.slo.evaluation` e
`streaming.slo.unresolved`. `knowledge/transport-diagnostics.md` declara que
`kafka.lag` e `kinesis.shard` carregam observações de lag/iterator age e que a
série temporal precisa de timestamps. O compositor já recebe `transport_key`,
mas o caminho `mode=slo` ainda não o encaminha para o avaliador.

## Perguntas feitas, uma por vez

1. A mudança precisa de superfície nova? Resposta operacional: não; o prompt
   já pede SLO e a CLI/MCP já expõem `mode=slo`, `transport_key` e as regras.
2. Qual evidência pode ser comparada? Resposta: somente `kafka.lag` e
   `kinesis.shard` com timestamp observado, identidade declarada e unidade
   compatível; métrica sem timestamp permanece unresolved.

## Escolha

A. O comparador existente continua sendo a única linguagem de avaliação. A
identidade muda de `query_name` para `transport_key` somente quando a declaração
indica fonte Kafka/Kinesis; nenhum threshold novo, causa ou custo é inventado.
