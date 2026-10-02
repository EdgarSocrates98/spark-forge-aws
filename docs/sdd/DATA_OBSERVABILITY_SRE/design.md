---
sdd: 1
feature: DATA_OBSERVABILITY_SRE
phase: design
profile: dev
status: ready
upstream:
  path: docs/sdd/DATA_OBSERVABILITY_SRE/define.md
  sha256: "5b81abcfca0a7b0ed88954f9e68eeb7bc0afb0bc4a18bed6a3d9ac9a6fc3f525"
files:
  - {path: sparkforge/observability/sre.py, action: create, reason: "SLO, error budget, incident e dependency evaluator."}
  - {path: sparkforge/observability/__init__.py, action: modify, reason: "Exporta API da camada SRE."}
  - {path: sparkforge/adapters/_core.py, action: modify, reason: "Analisador comum."}
  - {path: sparkforge/adapters/cli.py, action: modify, reason: "Verbo analyze data-observability."}
  - {path: sparkforge/adapters/tools.py, action: modify, reason: "Tool MCP read-only."}
  - {path: parity.yaml, action: modify, reason: "Paridade da observabilidade."}
  - {path: docs/surface.lock.json, action: modify, reason: "Registro exigido por nova tool MCP."}
  - {path: docs/guia/referencia/README.md, action: modify, reason: "Índice gerado da referência."}
  - {path: docs/guia/referencia/cli/analyze.md, action: modify, reason: "Referência gerada do verbo."}
  - {path: docs/guia/referencia/tools/README.md, action: modify, reason: "Índice gerado das tools."}
  - {path: docs/guia/referencia/tools/sparkforge_analyze_data_observability.md, action: create, reason: "Referência gerada da nova tool."}
  - {path: fixtures/observability/sre.yaml, action: create, reason: "Fixture OTel-like de SLOs e incidentes."}
  - {path: tests/test_data_observability.py, action: create, reason: "Avaliação de SLO e incidentes."}
  - {path: docs/knowledge/data-observability-sre.md, action: create, reason: "Guia e limites."}
decisions:
  - id: D1
    choice: "Cálculo só usa medições e objetivos presentes no artefato."
    rejected: ["preencher ausência com zero", "ler métricas live durante analyze"]
    rollback: "git revert da feature; nenhum sistema externo é tocado."
  - id: D2
    choice: "MTTR usa timestamps ISO explícitos e fica unresolved quando incidente está aberto."
    rejected: ["estimar encerramento", "usar horário atual implícito"]
    rollback: "git revert do avaliador de incidentes."
covers:
  - {part: "SLO evaluator", acceptance: [AC1]}
  - {part: "SRE context", acceptance: [AC2]}
  - {part: "surfaces", acceptance: [AC3]}
---

# DATA_OBSERVABILITY_SRE — desenho

```text
OTel-like dump + SLO spec
            |
            v
numeric measurements -> SLI status/error budget
incidents/deps/impact -> MTTR/health/blast-radius context
            |
            v
        CLI / MCP
```
