---
sdd: 1
feature: SNAPSHOT_GOLDEN_PROPAGATION
phase: design
profile: dev
status: ready
upstream:
  path: docs/sdd/SNAPSHOT_GOLDEN_PROPAGATION/define.md
  sha256: "99e52d2b0db8b68753a7b3b2877c278310de3568e2a842aacf1031570ba79257"
files:
  - {path: fixtures/cloudwatch_logs, action: modify, reason: "Alinhar facts e kinds das três fixtures com snapshots."}
  - {path: fixtures/consumers, action: modify, reason: "Alinhar facts e kinds das três fixtures com snapshots."}
  - {path: scripts/regen_fixtures.py, action: modify, reason: "Usar regeneradores oficiais sem alterar o script; manifesto registra o par runner/regenerador."}
decisions:
  - id: D1
    choice: "Regenerar somente seis nomes explícitos e revisar zero findings alterados."
    rejected: ["Regenerar corpus inteiro", "Editar JSON manualmente"]
    rollback: "git revert do commit desta feature."
covers:
  - {part: "composed fixture expectations", acceptance: [AC1, AC2]}
---

# SNAPSHOT_GOLDEN_PROPAGATION — desenho

O comportamento atual é intencional: runners que extraem o dump Iceberg devem
preservar `iceberg.snapshot`. A alteração é somente a projeção do output
esperado e da declaração do kind nos seis casos observados.
