---
sdd: 1
feature: STREAMING_FLINK_PLATFORM
phase: explore
profile: dev
status: ready
approaches:
  - id: A
    summary: "Analyzer offline comum para Apache Flink e Managed Flink, com namespaces separados e unresolved explícito."
    tradeoffs:
      - "um envelope CLI/MCP e fixtures compartilhados"
      - "não substitui matriz de versões nem collector live"
  - id: B
    summary: "Dois analyzers independentes, um para cada produto."
    tradeoffs:
      - "isolamento de payload"
      - "duplicação de surface, testes e contrato"
chosen: A
---

# STREAMING_FLINK_PLATFORM — exploração

## Problema

O prompt exige Flink e Managed Flink como domínios de primeira classe, mas o
repositório atual só possui conhecimento genérico de streaming. Precisamos
preservar a diferença entre runtime upstream e serviço AWS sem inventar
compatibilidade, e começar por artefatos salvos antes de qualquer collector.

## Escopo desta wave

Extrair configuração/estado/checkpoint/backpressure observados em JSON/JSONL,
expor CLI/MCP, criar fixtures positivas/negativas/unresolved, regras somente
para eventos medidos e skill/agente que encaminhem a evidência. Matriz completa
de versões e collector Managed Flink ficam como lacunas nomeadas.

## Perguntas respondidas

1. O parser acessa runtime? Não. Lê apenas dumps locais.
2. Flink upstream e Managed Flink compartilham facts? Somente o envelope; os
   namespaces e campos permanecem separados.
3. Backpressure vira finding por existir? Não. O finding exige métrica observada.
