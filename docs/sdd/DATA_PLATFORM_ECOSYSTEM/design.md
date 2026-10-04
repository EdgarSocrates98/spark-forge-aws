---
sdd: 1
feature: DATA_PLATFORM_ECOSYSTEM
phase: design
profile: dev
status: ready
upstream:
  path: docs/sdd/DATA_PLATFORM_ECOSYSTEM/define.md
  sha256: "331bed683bccce99cbb80f4db3af45f0c9a55421e78a2a5215d02ff7ba29479f"
files:
  - {path: sparkforge/platform/ecosystem.py, action: create, reason: "Contrato de serving/ingestion/AI/radar e reliability."}
  - {path: sparkforge/platform/__init__.py, action: modify, reason: "Exporta o inventário transversal."}
  - {path: sparkforge/adapters/_core.py, action: modify, reason: "Analisador comum."}
  - {path: sparkforge/adapters/cli.py, action: modify, reason: "Verbo analyze platform-ecosystem."}
  - {path: sparkforge/adapters/tools.py, action: modify, reason: "Tool MCP read-only."}
  - {path: parity.yaml, action: modify, reason: "Paridade do inventário."}
  - {path: docs/surface.lock.json, action: modify, reason: "Registro exigido por nova tool MCP."}
  - {path: docs/guia/referencia/README.md, action: modify, reason: "Índice gerado da referência."}
  - {path: docs/guia/referencia/cli/analyze.md, action: modify, reason: "Referência gerada do verbo."}
  - {path: docs/guia/referencia/tools/README.md, action: modify, reason: "Índice gerado das tools."}
  - {path: docs/guia/referencia/tools/sparkforge_analyze_platform_ecosystem.md, action: create, reason: "Referência gerada da nova tool."}
  - {path: fixtures/platform/ecosystem.yaml, action: create, reason: "Fixture com os domínios do prompt."}
  - {path: tests/test_platform_ecosystem.py, action: create, reason: "Domínios, reliability e radar."}
  - {path: docs/knowledge/data-platform-ecosystem.md, action: create, reason: "Guia transversal."}
decisions:
  - id: D1
    choice: "Categorias de produto e reliability controls ficam num contrato único e extensível."
    rejected: ["um parser hardcoded por vendor", "aceitar produto sem owner/evidence silenciosamente"]
    rollback: "git revert da feature."
  - id: D2
    choice: "Beam/DataHub/OpenMetadata têm role radar e não entram em dependencies de runtime."
    rejected: ["adicionar dependência obrigatória", "ignorar integrações no inventário"]
    rollback: "git revert da classificação radar."
covers:
  - {part: "ecosystem contract", acceptance: [AC1, AC2]}
  - {part: "CLI/MCP", acceptance: [AC3]}
---

# DATA_PLATFORM_ECOSYSTEM — desenho

```text
ecosystem.yaml -> systems + reliability + integrations
                               |
                               +-> category/kind/owner/source
                               +-> unresolved controls/references
                               +-> Platform Graph fragment / CLI / MCP
```
