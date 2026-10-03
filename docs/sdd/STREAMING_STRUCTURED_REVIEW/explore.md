---
sdd: 1
feature: STREAMING_STRUCTURED_REVIEW
phase: explore
profile: dev
status: ready
approaches:
  - id: A
    summary: "Skill dedicada que compõe source AST, progress e checkpoint offline."
    tradeoffs: ["não executa replay nem mede workload ausente"]
  - id: B
    summary: "Adicionar instruções somente ao arquiteto realtime existente."
    tradeoffs: ["roteamento perde precisão e o workflow não é avaliável isoladamente"]
chosen: A
---

# STREAMING_STRUCTURED_REVIEW — exploração

Facts e rules Structured Streaming já existem para source e
`StreamingQueryProgress`, mas o caminho de uso estava distribuído entre skills
genéricas. A skill dedicada fecha o workflow sem criar lógica paralela: orienta
analyzers existentes, preserva `unresolved`, exige runtime e termina em
validação funcional/rollback.

Fora do escopo: executar Spark, coletar AWS, provar replay, benchmark ou
exactly-once end-to-end sem artefatos do operador.
