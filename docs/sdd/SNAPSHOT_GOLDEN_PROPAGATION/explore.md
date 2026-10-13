---
sdd: 1
feature: SNAPSHOT_GOLDEN_PROPAGATION
phase: explore
profile: dev
status: ready
approaches:
  - id: A
    summary: "Regenerar somente os seis goldens compostos que passaram a emitir iceberg.snapshot e atualizar expects_kinds."
    tradeoffs: ["corrige drift medido", "aumenta facts esperados em dois runners"]
  - id: B
    summary: "Suprimir snapshots nos runners compostos ou relaxar o teste de kinds."
    tradeoffs: ["menor diff", "perde evidência temporal e enfraquece o gate"]
chosen: A
---

# SNAPSHOT_GOLDEN_PROPAGATION — exploração

O extrator Iceberg é reutilizado por runners compostos de CloudWatch Logs e
Consumers. O novo kind temporal já foi reconciliado em `fixtures/iceberg`, mas
esses dois corpus ainda têm snapshots observáveis ausentes dos facts esperados e
de `expects_kinds`.

Escopo desta feature: seis fixtures explicitamente afetadas, regeneração pelo
script oficial e cobertura dos dois runners. Glue cross-artifact, scan e cenários
ficam fora porque seus drifts têm causas diferentes.
