---
sdd: 1
feature: STREAMING_INTEGRATIONS_AND_CHECKPOINTS
phase: explore
profile: dev
status: ready
approaches:
  - id: A
    summary: "Contrato offline unificado para checkpoint, Kafka Connect, Kafka Streams e OpenLineage."
    tradeoffs: ["exige dump sanitizado", "não prova estado live"]
  - id: B
    summary: "Clientes live dentro do core para coletar Kafka e lineage."
    tradeoffs: ["quebra offline guarantee", "mistura credencial com extração"]
chosen: A
---

# STREAMING_INTEGRATIONS_AND_CHECKPOINTS — exploração

O prompt exige checkpoint metadata, Connect, Streams e OpenLineage como
capabilities diagnosáveis. O núcleo deve preservar a fronteira offline: recebe
artefato sanitizado, extrai fatos estáveis e nomeia o que só collector live pode
destravar.

Escopo: artifact contract, extractor, unresolved, rules, fixtures, knowledge,
analyzer CLI/MCP, SDD e integração nos gates. Collector live, replay funcional e
benchmark temporal são `N/A + motivo`: exigem endpoint, credencial, janela e
workload reais.
