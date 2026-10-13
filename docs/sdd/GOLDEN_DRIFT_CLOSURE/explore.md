---
sdd: 1
feature: GOLDEN_DRIFT_CLOSURE
phase: explore
profile: dev
status: ready
approaches:
  - id: A
    summary: "Regenerar os sete goldens residuais com os regeneradores oficiais de cada corpus e validar os runners completos."
    tradeoffs: ["fecha drift medido", "atualiza outputs derivados de três domínios"]
  - id: B
    summary: "Relaxar asserts ou manter goldens antigos."
    tradeoffs: ["menor diff", "oculta mudança de contrato e quebra paridade"]
chosen: A
---

# GOLDEN_DRIFT_CLOSURE — exploração

Após as duas reconciliações de `iceberg.snapshot`, o subset residual tem sete
falhas: três fixtures de composição Glue efetivo→Terraform, o cenário de scan
`misto` e os três cenários de migração. Cada grupo possui causa observada e
regenerador existente; nenhum requer mudança de produção.
