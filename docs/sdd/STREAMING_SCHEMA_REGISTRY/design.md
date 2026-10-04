---
sdd: 1
feature: STREAMING_SCHEMA_REGISTRY
phase: design
profile: dev
status: ready
upstream:
  path: docs/sdd/STREAMING_SCHEMA_REGISTRY/define.md
  sha256: "96b86fe4ec27371154ffb33d2999a41a0ac5f07c20a4d1ac6eb9af09172afe76"
files:
  - {path: sparkforge/facts/schema_registry.py, action: create, reason: "extrator offline de contratos e diffs"}
  - {path: rules/catalog/schema_registry.yaml, action: create, reason: "regras de compatibilidade e governança"}
  - {path: fixtures/schema_registry, action: create, reason: "goldens positivos, incompatíveis e unresolved"}
  - {path: sparkforge/adapters/_core.py, action: modify, reason: "envelope comum para analyze schema-registry"}
  - {path: sparkforge/adapters/cli.py, action: modify, reason: "adicionar analyze schema-registry"}
  - {path: sparkforge/adapters/tools.py, action: modify, reason: "adicionar tool MCP read-only"}
  - {path: skills/review-cdc-replication/SKILL.md, action: modify, reason: "workflow de contrato e compatibilidade"}
  - {path: rules/catalog/routing.yaml, action: modify, reason: "rotear SF-SCHEMA para especialista"}
decisions:
  - id: D1
    choice: "Schema Registry permanece namespace próprio e o diff estrutural é marcado como proxy."
    rejected: ["misturar com cdc.*", "afirmar compatibilidade end-to-end"]
    rollback: "Remover analyzer, rules e fixtures de schema; manter knowledge offline."
  - id: D2
    choice: "Política ou definição ausente emite unresolved e bloqueia julgamento dependente."
    rejected: ["usar BACKWARD como default", "inferir compatibilidade pelo formato"]
    rollback: "Retirar findings dependentes e preservar facts observados."
  - id: D3
    choice: "A tool é read-only e não publica schema."
    rejected: ["registro automático dentro do analyzer", "consulta remota implícita"]
    rollback: "Reverter superfície e paridade sem alterar registry."
covers:
  - {part: "facts e unresolved", acceptance: [AC1]}
  - {part: "fixtures e rules", acceptance: [AC2, AC3]}
  - {part: "CLI/MCP", acceptance: [AC4]}
  - {part: "skill e registros", acceptance: [AC5]}
---

# STREAMING_SCHEMA_REGISTRY — desenho

`schema_registry.py` lê JSON/JSONL e emite `schema.registry`,
`schema.definition`, `schema.compatibility`, `schema.diff`, `schema.unresolved`
e `schema.analyzed`. O diff é proxy estrutural e registra added/removed/type
changes/required changes; sem schema anterior ou política, a lacuna fica visível.

`SF-SCHEMA` mantém regras executáveis e rota para `cdc-contract-reviewer`.
