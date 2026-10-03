---
sdd: 1
feature: STREAMING_KINESIS_TEMPORAL_METRICS
phase: explore
profile: dev
status: ready
approaches:
  - id: A
    summary: "Estender collect streaming-integrations com janela CloudWatch opcional para métricas stream-level do Kinesis."
    tradeoffs:
      - "reutiliza artifact, CLI, MCP e manifesto existentes"
      - "o payload do collector passa a ter dois modos de evidência"
  - id: B
    summary: "Criar collector, verbo e tool separados para métricas Kinesis."
    tradeoffs:
      - "separa contratos de snapshot e série"
      - "aumenta surface, custo de contexto e caminhos de cache"
chosen: A
---

# STREAMING_KINESIS_TEMPORAL_METRICS — exploração

## Pergunta operacional

Como reduzir o blind spot atual em que o snapshot Kinesis conhece stream/shards,
mas lag, throughput e throttling continuam `unresolved`, sem criar uma nova
tool MCP para cada API AWS?

## Escolha

A. A API CloudWatch é uma extensão temporal do snapshot Kinesis já coletado.
Manter o verbo composto preserva paridade, manifesto e economia de contexto; a
janela explícita evita transformar uma leitura pontual em tendência.

## Limite

Esta frente consulta somente métricas stream-level documentadas em
`AWS/Kinesis`: `IncomingBytes`, `IncomingRecords`,
`GetRecords.IteratorAgeMilliseconds`, `ReadProvisionedThroughputExceeded` e
`WriteProvisionedThroughputExceeded`. Métricas shard-level exigem enhanced
monitoring e permanecem fora até existir declaração explícita de shards e custo.
