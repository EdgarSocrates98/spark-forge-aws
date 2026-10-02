---
sdd: 1
feature: OPEN_LAKEHOUSE_CATALOG
phase: design
profile: dev
status: ready
upstream:
  path: docs/sdd/OPEN_LAKEHOUSE_CATALOG/define.md
  sha256: "5ba90f4f78e4ac5df3b858ec5ea8cb40d10ba35e30d2d43b837f1f253b3b52e9"
files:
  - {path: sparkforge/catalog/__init__.py, action: create, reason: "API pública do contrato de catalog topology."}
  - {path: sparkforge/catalog/contract.py, action: create, reason: "Loader, sanitização, validação e fingerprint."}
  - {path: sparkforge/adapters/_core.py, action: modify, reason: "Analisador compartilhado CLI/MCP."}
  - {path: sparkforge/adapters/cli.py, action: modify, reason: "Verbo analyze lakehouse-catalog."}
  - {path: sparkforge/adapters/tools.py, action: modify, reason: "Tool MCP read-only."}
  - {path: parity.yaml, action: modify, reason: "Declara paridade de catálogo."}
  - {path: docs/surface.lock.json, action: modify, reason: "Registro exigido por nova tool MCP."}
  - {path: docs/guia/referencia/README.md, action: modify, reason: "Índice gerado da referência."}
  - {path: docs/guia/referencia/cli/analyze.md, action: modify, reason: "Referência gerada do verbo."}
  - {path: docs/guia/referencia/tools/README.md, action: modify, reason: "Índice gerado das tools."}
  - {path: docs/guia/referencia/tools/sparkforge_analyze_lakehouse_catalog.md, action: create, reason: "Referência gerada da nova tool."}
  - {path: contracts/lakehouse-catalog-v1.schema.json, action: create, reason: "Contrato publicável."}
  - {path: fixtures/platform/catalog.yaml, action: create, reason: "Topologia sintética multi-catalog."}
  - {path: tests/test_lakehouse_catalog.py, action: create, reason: "Determinismo, sanitização e paridade."}
  - {path: docs/knowledge/open-lakehouse-catalog.md, action: create, reason: "Guia de integração e limites."}
decisions:
  - id: D1
    choice: "Catalog/engine compatibility é declaração com evidence, não matriz inventada."
    rejected: ["hardcode de versões e capacidades", "prober live no analyze"]
    rollback: "git revert do commit do contrato e remover a nova superfície."
  - id: D2
    choice: "Secrets são recusados e endpoints são tratados como identificadores declarados."
    rejected: ["persistir token no manifesto", "normalizar URL privada como credencial"]
    rollback: "git revert do sanitizador; nenhum segredo válido deve ter entrado."
covers:
  - {part: "catalog contract", acceptance: [AC1]}
  - {part: "CLI/MCP", acceptance: [AC2]}
---

# OPEN_LAKEHOUSE_CATALOG — desenho

```text
catalog.yaml -> sanitize/validate -> canonical topology/fingerprint
                                      |
                                      +-> catalogs + engines + tables + bindings
                                      +-> unresolved
                                      +-> CLI / MCP / future graph fragment
```
