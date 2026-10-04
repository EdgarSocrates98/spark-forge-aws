---
sdd: 1
feature: STREAMING_SCHEMA_REGISTRY
phase: explore
profile: dev
status: ready
approaches:
  - id: A
    summary: "Um extrator offline para registry, definição e diff estrutural."
    tradeoffs: ["reaproveita CLI/MCP e rules", "não prova consumidores vivos"]
  - id: B
    summary: "Collectors contra registries remotos."
    tradeoffs: ["evidência operacional mais rica", "viola núcleo offline e exige credenciais"]
chosen: A
---

# STREAMING_SCHEMA_REGISTRY — exploração

O prompt exige contratos de schema alcançáveis antes de discutir compatibilidade
de produção. A wave lê somente dumps locais e fecha o caminho de evidência:
registry/subject, formato, versão, definição, política, diff e lacunas.

Alternativas descartadas: chamar AWS/Confluent no núcleo; inferir consumidores;
afirmar compatibilidade end-to-end a partir de um JSON isolado.
