---
sdd: 1
feature: STREAMING_SLO_TRANSPORT_EVALUATION
phase: design
profile: dev
status: ready
upstream:
  path: docs/sdd/STREAMING_SLO_TRANSPORT_EVALUATION/define.md
  sha256: "e310787a557e53029756f082fab89239b0a2b432f95d4a0fc8283dc6a0ed1e05"
files:
  - {path: sparkforge/facts/streaming_slo.py, action: modify, reason: "comparar observações diretas de kafka.lag e kinesis.shard com unidade e janela"}
  - {path: sparkforge/facts/streaming.py, action: modify, reason: "preservar identidade temporal da progress existente sem regressão"}
  - {path: sparkforge/facts/transport.py, action: modify, reason: "preservar timestamp textual de métricas Kinesis e identidade de stream quando necessário"}
  - {path: sparkforge/facts/streaming_composition.py, action: modify, reason: "encaminhar transport_key ao avaliador SLO"}
  - {path: sparkforge/adapters/_core.py, action: modify, reason: "manter core único e read-only"}
  - {path: sparkforge/adapters/cli.py, action: modify, reason: "documentar source/transport no modo existente sem novo verbo"}
  - {path: sparkforge/adapters/tools.py, action: modify, reason: "descrever SLO de transporte no schema MCP existente"}
  - {path: tests/test_facts_streaming_slo.py, action: modify, reason: "testes vermelhos e verdes para Kafka/Kinesis"}
  - {path: tests/test_analyze_streaming_composition.py, action: modify, reason: "paridade CLI/MCP do transport_key"}
  - {path: tests/test_fixtures_golden_streaming_composition.py, action: modify, reason: "registrar goldens SLO transport"}
  - {path: fixtures/streaming_composition/slo_kafka_met, action: create, reason: "golden de lag Kafka coberto"}
  - {path: fixtures/streaming_composition/slo_kinesis_violated, action: create, reason: "golden de iterator age Kinesis violado"}
  - {path: fixtures/streaming_composition/slo_transport_unresolved, action: create, reason: "golden de identidade ou timestamp incompleto"}
  - {path: knowledge/transport-diagnostics.md, action: modify, reason: "registrar avaliação SLO de transporte e limites"}
  - {path: skills/analyze-streaming-composition/SKILL.md, action: modify, reason: "ensinar fluxo SLO Kafka/Kinesis com detail econômico"}
  - {path: docs/streaming/prompt-coverage.md, action: modify, reason: "atualizar cobertura observability/SLO"}
  - {path: tests/test_docs_coverage.py, action: modify, reason: "cobrir a entrega documental"}
decisions:
  - id: D1
    choice: "Reutilizar mode=slo, as regras SF-STREAM-011/012 e o envelope existente; transport_key é identidade declarada para Kafka/Kinesis."
    rejected: ["modo novo por serviço, que duplicaria surface e comparador", "bridge em data-observability, que perderia identidade de transporte"]
    rollback: "Reverter o commit da extensão; o mode=slo volta a avaliar apenas progress sem alterar os fatos de transporte existentes."
  - id: D2
    choice: "Aceitar somente kafka.lag e kinesis.shard com timestamp textual timezone-aware; não transformar kinesis.metric sem timestamp em série."
    rejected: ["usar ordem do arquivo como tempo", "converter timestamp numérico sem unidade declarada", "agregar shards ou grupos diferentes"]
    rollback: "Remover as fontes adicionais da allowlist e preservar unresolved para qualquer série não compatível."
covers:
  - {part: "comparador SLO e identidade de transporte", acceptance: [AC1, AC2, AC3]}
  - {part: "portas existentes", acceptance: [AC4]}
  - {part: "fixtures e regressão", acceptance: [AC5]}
  - {part: "knowledge, skill e gates", acceptance: [AC6]}
---

# STREAMING_SLO_TRANSPORT_EVALUATION — desenho

## Conhecimento consultado

- `sparkforge rules lookup --category streaming_slo`: `SF-STREAM-004`,
  `SF-STREAM-011` e `SF-STREAM-012`, consultado em 2026-10-02.
- `knowledge/transport-diagnostics.md`: namespaces `kafka.lag` e
  `kinesis.shard`, limites de timestamp, identidade e ausência de inferência.
- `prompt_evo_streaming.md`, seções 19, 20, 24, 25, 33 e 44: observabilidade,
  SLO, collectors, superfície e economia de contexto.
