---
sdd: 1
feature: ICEBERG_GOLDEN_RECONCILIATION
phase: explore
profile: dev
status: ready
approaches:
  - id: A
    summary: "Regenerar somente goldens Iceberg afetados pela emissão intencional de iceberg.snapshot e atualizar expects_kinds com revisão do diff."
    tradeoffs: ["corrige drift medido sem tocar outros domínios", "aumenta snapshots esperados nos casos legados"]
  - id: B
    summary: "Suprimir iceberg.snapshot em fixtures legadas ou alterar o extrator para preservar o corpus antigo."
    tradeoffs: ["reduz diff imediato", "perde granularidade necessária para composição temporal e reabre o defeito"]
chosen: A
---

# ICEBERG_GOLDEN_RECONCILIATION — exploração

O extrator `iceberg_metadata@0.1.0` passou a emitir `iceberg.snapshot` por
observação temporal em `171074b`. A suíte atual mede 14 fixtures com kind
observado, mas `meta.yaml` e `expected/facts.json` ainda refletem o corpus
anterior. A alternativa A preserva o comportamento observado e reconcilia
somente os goldens cujo teste falha; nenhuma execução externa é necessária.
