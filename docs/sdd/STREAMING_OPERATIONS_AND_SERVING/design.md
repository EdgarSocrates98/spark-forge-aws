---
sdd: 1
feature: STREAMING_OPERATIONS_AND_SERVING
phase: design
profile: dev
status: ready
upstream:
  path: docs/sdd/STREAMING_OPERATIONS_AND_SERVING/define.md
  sha256: "e1ae118b33212f47531e20e207b4807a151d34e6ed19e12aff51f413d874059c"
files:
  - {path: sparkforge/facts/streaming_ops.py, action: create, reason: "extrair contrato operacional offline com redaction"}
  - {path: sparkforge/adapters/_core.py, action: modify, reason: "publicar facts no core de análise"}
  - {path: sparkforge/adapters/cli.py, action: modify, reason: "adicionar analyze streaming-ops"}
  - {path: sparkforge/adapters/tools.py, action: modify, reason: "adicionar MCP read-only"}
  - {path: rules/catalog/streaming-operations.yaml, action: create, reason: "julgar lacunas SLO FinOps segurança"}
  - {path: fixtures/streaming_ops, action: create, reason: "corpus complete missing redaction"}
  - {path: tests/test_facts_streaming_ops.py, action: create, reason: "contrato e redaction"}
  - {path: tests/test_analyze_streaming_ops.py, action: create, reason: "paridade CLI/MCP"}
  - {path: knowledge/streaming-operations.md, action: create, reason: "fontes operacionais e limites"}
  - {path: knowledge/streaming-format-serving-matrix.md, action: create, reason: "compatibilidade declarativa sem benchmark"}
  - {path: skills/review-streaming-operations/SKILL.md, action: create, reason: "workflow evidence-first"}
  - {path: agents/streaming-realtime-architect.md, action: modify, reason: "expor skill operacional"}
decisions:
  - id: D1
    choice: "Contrato JSON offline, com um fact por declaração válida e unresolved por lacuna."
    rejected: ["inferir SLO ou custo por nome do serviço", "consultar AWS no extrator"]
    rollback: "Remover extrator, adapters, regras, fixtures e skill; preservar referências como conhecimento."
  - id: D2
    choice: "Redact campos sensíveis antes de criar Fact."
    rejected: ["copiar secrets para evidência", "tratar Secrets Manager como valor secreto"]
    rollback: "Desabilitar persistência dos campos e manter apenas unresolved do caminho."
  - id: D3
    choice: "MCP segue envelope de análise existente e não cria endpoint separado para cada domínio."
    rejected: ["cinco tools duplicadas", "retorno fora do contrato Fact/page"]
    rollback: "Remover tool mantendo o comando CLI e o extrator offline."
covers:
  - {part: "facts, measures and redaction", acceptance: [AC1, AC2]}
  - {part: "fixtures, rules and envelopes", acceptance: [AC3, AC4]}
  - {part: "knowledge, skill and generated surfaces", acceptance: [AC5]}
---

# STREAMING_OPERATIONS_AND_SERVING — desenho

O analisador compõe cinco seções declarativas. A regra só dispara sobre
`streaming_ops.unresolved`; ausência de evidência não vira controle ausente.
