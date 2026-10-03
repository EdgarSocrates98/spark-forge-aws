---
sdd: 1
feature: STREAMING_END_TO_END_PIPELINE
phase: explore
profile: dev
status: ready
approaches:
  - id: A
    summary: "Adicionar modo pipeline ao compositor streaming existente, consumindo contrato declarativo e facts já extraídos."
    tradeoffs:
      - "Mantém uma única superfície CLI/MCP e reutiliza provenance, paginação e judge."
      - "Exige selectors explícitos no contrato; não descobre topologia por nome ou ordem de arquivos."
  - id: B
    summary: "Criar um analyzer e tool independentes para topologias end-to-end."
    tradeoffs:
      - "Contrato isolado poderia evoluir livremente."
      - "Duplicaria leitura, paginação, surface lock e integração com os analyzers existentes."
  - id: C
    summary: "Inferir a cadeia automaticamente a partir dos kinds presentes nos facts."
    tradeoffs:
      - "Menos configuração inicial."
      - "Transformaria coexistência de artifacts em vínculo não observado e produziria falsos positivos."
chosen: A
---

# STREAMING_END_TO_END_PIPELINE — exploração

## Perfil

`dev`: a mudança é no próprio SparkForge e permanece offline-first.

## Perguntas feitas e decisão

1. Qual lacuna operacional foi medida? A cobertura de streaming confirma que
   CDC, transporte, processamento, sink e schema possuem facts separados, mas
   não há uma composição declarativa que prove cada aresta do pipeline.
2. Como preservar o contrato evidence-first? A cadeia deve ser declarada por
   selectors (`kind` + atributos exatos), e cada node/edge precisa carregar os
   `fact_id` que o sustentam ou um `unresolved` nomeado.
3. O que evita crescimento desnecessário de superfície? A modalidade entra no
   compositor `sparkforge analyze streaming-composition`; não nasce tool nova.

## Abordagens

A é escolhida. Ela fecha a lacuna de integração com uma mudança aditiva,
econômica em contexto e compatível com o envelope atual de facts. B fica
rejeitada por duplicar superfície; C fica rejeitada porque presença de fatos não
prova topologia nem identidade.

## Escolha

A, porque o coordenador recebe um resumo compacto de nodes, edges, blind spots e
ids de evidência sem reabrir todos os artifacts. O contrato continua humano,
versionável e fail-closed.
