---
sdd: 1
feature: ORCHESTRATION_CONTROL_PLANE
phase: design
profile: dev
status: ready
upstream:
  path: docs/sdd/ORCHESTRATION_CONTROL_PLANE/define.md
  sha256: "477ee8ce807a5404359cabc5870128e712ad3fc2aeba61ae56982a56828dcba3"
files:
  - {path: sparkforge_aws/orchestration/__init__.py, action: create, reason: "API normalizada de orchestration control plane."}
  - {path: sparkforge_aws/orchestration/topology.py, action: create, reason: "Loader, normalização e unresolved."}
  - {path: sparkforge_aws/adapters/_core.py, action: modify, reason: "Analisador compartilhado."}
  - {path: sparkforge_aws/adapters/cli.py, action: modify, reason: "Verbo analyze orchestration."}
  - {path: sparkforge_aws/adapters/tools.py, action: modify, reason: "Tool MCP read-only."}
  - {path: parity.yaml, action: modify, reason: "Paridade do orchestration map."}
  - {path: docs/surface.lock.json, action: modify, reason: "Registro exigido por nova tool MCP."}
  - {path: docs/guia/referencia/README.md, action: modify, reason: "Índice gerado da referência."}
  - {path: docs/guia/referencia/cli/analyze.md, action: modify, reason: "Referência gerada do verbo."}
  - {path: docs/guia/referencia/tools/README.md, action: modify, reason: "Índice gerado das tools."}
  - {path: docs/guia/referencia/tools/sparkforge_analyze_orchestration.md, action: create, reason: "Referência gerada da nova tool."}
  - {path: fixtures/orchestration/control-plane.yaml, action: create, reason: "Fixture multi-orchestrator."}
  - {path: tests/test_orchestration.py, action: create, reason: "Controles e unresolved."}
  - {path: docs/knowledge/orchestration-control-plane.md, action: create, reason: "Guia operacional."}
decisions:
  - id: D1
    choice: "Normalizar campos sem apagar bloco de configuração original."
    rejected: ["um schema exclusivo por plataforma", "reduzir workflow a nome e dependências"]
    rollback: "git revert da feature."
  - id: D2
    choice: "Analyze é read-only e não dispara nenhum orquestrador."
    rejected: ["backfill automático", "retry automático para validar configuração"]
    rollback: "git revert; nenhum sistema externo foi acionado."
covers:
  - {part: "normalized topology", acceptance: [AC1, AC2]}
  - {part: "CLI/MCP", acceptance: [AC3]}
---

# ORCHESTRATION_CONTROL_PLANE — desenho

```text
orchestration.yaml -> normalize -> workflow controls + source config
                                  -> unresolved dependency/control
                                  -> CLI / MCP / Platform Graph fragment
```
