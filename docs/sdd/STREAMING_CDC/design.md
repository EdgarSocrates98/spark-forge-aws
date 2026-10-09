---
sdd: 1
feature: STREAMING_CDC
phase: design
profile: dev
status: ready
upstream:
  path: docs/sdd/STREAMING_CDC/define.md
  sha256: "5b117652ff46a1e2bce4591bbe73468c77b23b3c7071e85dc9675a0e983025c2"
files:
  - {path: sparkforge_aws/facts/cdc.py, action: create, reason: "extrator JSON/JSONL offline CDC, Debezium e DMS"}
  - {path: rules/catalog/cdc.yaml, action: create, reason: "regras de posição, chave, tombstone, seam, schema history e mappings"}
  - {path: fixtures/cdc, action: create, reason: "goldens positivos, negativos e unresolved por vocabulário"}
  - {path: sparkforge_aws/adapters/_core.py, action: modify, reason: "envelope comum para analyze cdc"}
  - {path: sparkforge_aws/adapters/cli.py, action: modify, reason: "adicionar analyze cdc"}
  - {path: sparkforge_aws/adapters/tools.py, action: modify, reason: "adicionar tool MCP read-only"}
  - {path: skills/review-cdc-replication/SKILL.md, action: create, reason: "workflow evidence-first"}
  - {path: agents/cdc-contract-reviewer.md, action: create, reason: "especialista e rule areas CDC/Debezium/DMS/Schema"}
  - {path: rules/catalog/routing.yaml, action: modify, reason: "roteamento determinístico para especialista CDC"}
  - {path: parity.yaml, action: modify, reason: "paridade CLI/MCP/plataformas"}
decisions:
  - id: D1
    choice: "Namespaces cdc.*, debezium.* e dms.* separados dentro de um extractor e uma tool."
    rejected: ["misturar configuração e evento", "uma regra genérica por nome do serviço"]
    rollback: "Reverter analyzer, rules e fixtures CDC; manter apenas conhecimento documentado."
  - id: D2
    choice: "Posição, chave, tombstone e snapshot/CDC seam ausentes emitem unresolved."
    rejected: ["usar offset zero", "assumir chave por tabela", "declarar exatamente-once"]
    rollback: "Remover findings dependentes e manter facts observados sem defaults."
  - id: D3
    choice: "A tool é read-only e não chama serviços externos."
    rejected: ["collector oculto dentro do analyzer", "mutação durante review"]
    rollback: "Retirar a tool e reverter paridade; não altera infraestrutura."
covers:
  - {part: "facts e unresolved", acceptance: [AC1, AC2]}
  - {part: "fixtures e rules", acceptance: [AC3]}
  - {part: "CLI/MCP", acceptance: [AC4]}
  - {part: "skill, agente e registros", acceptance: [AC5]}
---

# STREAMING_CDC — desenho
