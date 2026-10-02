---
sdd: 1
feature: STREAMING_LAKEHOUSE_OBSERVABILITY
phase: design
profile: dev
status: ready
upstream:
  path: docs/sdd/STREAMING_LAKEHOUSE_OBSERVABILITY/define.md
  sha256: "223742092b42c8ff07952fdf7882197bf22f8ebe34c589af96b57a93e2e992e7"
files:
  - {path: sparkforge/facts/streaming_composition.py, action: create, reason: "composição pura sobre facts de streaming, transporte e Iceberg"}
  - {path: sparkforge/adapters/_core.py, action: modify, reason: "expor composição e carregar facts"}
  - {path: sparkforge/adapters/cli.py, action: modify, reason: "adicionar analyze streaming-composition"}
  - {path: sparkforge/adapters/tools.py, action: modify, reason: "adicionar tool MCP read-only"}
  - {path: rules/catalog/streaming_composition.yaml, action: create, reason: "rules para relação não-append e evidência de transporte"}
  - {path: fixtures/streaming_composition, action: create, reason: "goldens positivos, observáveis e unresolved"}
  - {path: skills/analyze-streaming-composition/SKILL.md, action: create, reason: "workflow evidence-first de correlação"}
  - {path: agents/streaming-realtime-architect.md, action: modify, reason: "declarar áreas compostas"}
  - {path: rules/catalog/routing.yaml, action: modify, reason: "rotear regras compostas para coordenador streaming"}
  - {path: parity.yaml, action: modify, reason: "registrar capability de composição"}
  - {path: docs/streaming/prompt-coverage.md, action: modify, reason: "auditar Wave G"}
decisions:
  - id: D1
    choice: "Um correlator com modo iceberg|observability e identidades declaradas."
    rejected: ["inferir relação pelo nome de arquivo ou proximidade temporal"]
    rollback: "Reverter o commit do correlator e remover a tool/surface composta."
  - id: D2
    choice: "Fact composto carrega ids dos fatos de origem, medidas e unresolved nomeado."
    rejected: ["copiar números para um resumo sem procedência"]
    rollback: "Remover os kinds compostos e voltar a julgar os extratores isoladamente."
  - id: D3
    choice: "Rule de Iceberg só acusa operação não-append observada; observabilidade não presume causa."
    rejected: ["limiar fixo de lag", "snapshot por batch automaticamente ruim"]
    rollback: "Reverter rules e preservar a composição factual."
covers:
  - {part: "composição Iceberg", acceptance: [AC1, AC3]}
  - {part: "composição observabilidade", acceptance: [AC2, AC3]}
  - {part: "surface e integração", acceptance: [AC4, AC5]}
---

# STREAMING_LAKEHOUSE_OBSERVABILITY — desenho

O vínculo é uma declaração do chamador confirmada por campos dos facts. O
correlator nunca usa somente ausência de finding para declarar saúde, e não
transforma uma relação temporal em root cause.
