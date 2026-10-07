---
sdd: 1
feature: STREAMING_SINK_SLO_EVALUATION
phase: design
profile: dev
status: ready
upstream:
  path: docs/sdd/STREAMING_SINK_SLO_EVALUATION/define.md
  sha256: "58c2caa0837a354ddc34f82d7e77dfbb1b8f937545e3a9377721efc252632a3a"
files:
  - {path: sparkforge_aws/facts/streaming_slo.py, action: modify, reason: "aceitar num_output_rows e ligar sink ao batch temporal"}
  - {path: sparkforge_aws/facts/streaming_ops.py, action: modify, reason: "preservar sink_name declarado no contrato SLO"}
  - {path: sparkforge_aws/adapters/tools.py, action: modify, reason: "documentar source streaming_sink e sink_name na superfície MCP existente"}
  - {path: sparkforge_aws/adapters/cli.py, action: modify, reason: "explicar source streaming_sink no modo SLO existente"}
  - {path: tests/test_facts_streaming_slo.py, action: modify, reason: "cobrir sink observado, vínculo temporal e recusas"}
  - {path: tests/test_analyze_streaming_composition.py, action: modify, reason: "paridade CLI/MCP do SLO de sink"}
  - {path: tests/test_fixtures_golden_streaming_composition.py, action: modify, reason: "registrar goldens de sink"}
  - {path: fixtures/streaming_composition, action: create, reason: "goldens met, violated e unresolved de sink"}
  - {path: knowledge/streaming-operations.md, action: modify, reason: "registrar métrica direta de saída e limites"}
  - {path: skills/analyze-streaming-composition/SKILL.md, action: modify, reason: "ensinar SLO de sink e evidência por batch"}
  - {path: docs/streaming/prompt-coverage.md, action: modify, reason: "atualizar cobertura de sink SLO"}
  - {path: tests/test_docs_coverage.py, action: modify, reason: "cobrir documentação da frente"}
decisions:
  - id: D1
    choice: "Reutilizar mode=slo e o envelope atual; streaming_sink é fonte declarada e query_name é identidade obrigatória."
    rejected: ["modo novo de sink, que duplicaria CLI/MCP e regras", "SLO genérico sem batch, que perderia prova temporal"]
    rollback: "Remover a fonte streaming_sink da allowlist e preservar unresolved para contratos de sink."
  - id: D2
    choice: "Usar batch_id e arquivo de origem para ligar sink ao batch; sem correspondência ou com descrição ambígua, recusar."
    rejected: ["usar ordem do arquivo como timestamp", "usar timestamp de parede do compositor", "agregar sinks sem identidade"]
    rollback: "Reverter somente o caminho de composição de sink; facts existentes permanecem compatíveis."
covers:
  - {part: "métrica e identidade", acceptance: [AC1, AC2, AC3]}
  - {part: "portas existentes", acceptance: [AC4]}
  - {part: "fixtures e regressão", acceptance: [AC5]}
  - {part: "knowledge, skill e gates", acceptance: [AC6]}
---

# STREAMING_SINK_SLO_EVALUATION — desenho

## Contrato

Exemplo de declaração:

```json
{"name":"sink-output","metric":"num_output_rows","operator":"gte","unit":"rows","window":"5m","source":"streaming_sink","sink_name":"iceberg-orders","target":90}
```

`streaming.progress.sink` fornece a medida; `streaming.progress.batch` do
mesmo arquivo e `batch_id` fornece timestamp e `query_name`. O comparador não
abre o artefato e não faz chamada externa.
