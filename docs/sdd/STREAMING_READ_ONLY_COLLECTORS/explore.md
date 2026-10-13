---
sdd: 1
feature: STREAMING_READ_ONLY_COLLECTORS
phase: explore
profile: dev
status: ready
approaches:
  - id: A
    summary: "Coletor AWS read-only composto, offline-first, para snapshots streaming."
    tradeoffs: ["não mede lag sem janela", "Connect/Streams/OpenLineage exigem endpoint próprio"]
  - id: B
    summary: "Embute clientes Kafka e lineage no core."
    tradeoffs: ["quebra offline guarantee", "credenciais e protocolos heterogêneos"]
chosen: A
---

# STREAMING_READ_ONLY_COLLECTORS — exploração

As waves offline já extraem checkpoint, Glue Streaming, Kinesis, MSK, DMS,
Kafka Connect, Kafka Streams e OpenLineage quando um dump existe. Faltava um
caminho operacional seguro para materializar snapshots AWS sem criar um
collector write-capable nem afirmar métricas temporais ausentes.

Escopo: coletor read-only para checkpoint S3, Glue, Kinesis, MSK e DMS;
manifesto/hash/cache; redaction; CLI/MCP; testes com clientes falsos. Lag,
replay, throughput, Connect REST, Kafka Streams runtime e OpenLineage live
continuam `N/A + motivo`.
