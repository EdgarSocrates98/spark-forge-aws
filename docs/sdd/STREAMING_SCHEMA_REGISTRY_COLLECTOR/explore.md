---
sdd: 1
feature: STREAMING_SCHEMA_REGISTRY_COLLECTOR
phase: explore
profile: dev
status: ready
approaches:
  - id: A
    summary: "Adicionar coleta read-only dedicada ao AWS Glue Schema Registry e reutilizar o analyzer offline existente."
    tradeoffs: ["surface nova justificável por objetivo P0", "requer paginação e limite explícito de schemas/definições"]
  - id: B
    summary: "Misturar Schema Registry no dump composto de streaming-integrations."
    tradeoffs: ["não aumenta surface", "mistura contrato de aquisição com vários analyzers e perde artifact kind próprio"]
chosen: A
---

# STREAMING_SCHEMA_REGISTRY_COLLECTOR — exploração

O repositório já analisa contratos salvos por `analyze schema-registry`, mas a
matriz de streaming ainda marca collectors/live registry como lacuna. O AWS
Glue Schema Registry oferece APIs read-only para listar registries/schemas,
descrever schema e obter a versão mais recente. A coleta dedicada preserva um
artifact próprio consumível pelo analyzer, sem criar mutação nem inferir
compatibilidade a partir de metadados ausentes.
