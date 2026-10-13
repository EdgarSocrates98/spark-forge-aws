---
sdd: 1
feature: STREAMING_SINK_SLO_EVALUATION
phase: define
profile: dev
status: ready
upstream:
  path: docs/sdd/STREAMING_SINK_SLO_EVALUATION/explore.md
  sha256: "109e15444dd2b8d513fcc2156f24920ab80997738586087e95587fb20b913175"
hypothesis:
  claim: "O comparador SLO existente consegue avaliar quantidade de saída observada no sink sem novo extractor ou nova superfície quando liga streaming.progress.sink ao batch correspondente."
  prediction: "Uma série com pelo menos duas observações de num_output_rows, query declarada, timestamps dos batches, unidade rows e janela coberta produz met ou violated; sink ausente, batch sem timestamp ou múltiplos sinks ambíguos produz somente streaming.slo.unresolved."
  experiment: "Extrair progress real sanitizado, declarar SLO source=streaming_sink, executar mode=slo por CLI/MCP e validar goldens met, violated e unresolved."
acceptance:
  - id: AC1
    statement: "A declaração streaming_sink exige query_name e aceita métrica num_output_rows com unidade rows e operador/target válidos."
    verified_by: {kind: test, ref: tests/test_facts_streaming_slo.py::test_evaluates_sink_output_slo}
  - id: AC2
    statement: "Cada observação de sink é ligada ao batch da mesma origem por batch_id; timestamp e query vêm do batch e source_fact_ids preserva ambos."
    verified_by: {kind: test, ref: tests/test_facts_streaming_slo.py::test_sink_slo_uses_batch_timestamp_and_provenance}
  - id: AC3
    statement: "Sink ausente, batch/timestamp ausente, unidade incorreta e múltiplas descrições sem sink_name resultam em unresolved nomeado."
    verified_by: {kind: test, ref: tests/test_facts_streaming_slo.py::test_sink_slo_unresolved_reasons}
  - id: AC4
    statement: "CLI e MCP preservam envelope idêntico para o modo SLO de sink sem criar tool nova."
    verified_by: {kind: test, ref: tests/test_analyze_streaming_composition.py::test_sink_slo_cli_and_mcp_envelopes_match}
  - id: AC5
    statement: "Goldens cobrem sink met, sink violated e sink unresolved, mantendo regressão dos modos progress e transporte."
    verified_by: {kind: test, ref: tests/test_fixtures_golden_streaming_composition.py::test_fixture_goldens}
  - id: AC6
    statement: "Knowledge, skill, prompt coverage, referências, surface lock, manifest e SDD registram a métrica e seus limites."
    verified_by: {kind: command, ref: python scripts/sync_skills.py --check}
success:
  - id: SC1
    metric: "Todos AC1–AC6 verdes; avaliação de sink permanece observacional e não declara freshness, p95, exactly-once, causa ou custo."
    source: "pytest focalizado, goldens, CLI/MCP e gates de superfície, documentação e bundle offline"
out_of_scope:
  - "Freshness, end-to-end latency, p95, availability, DLQ, replay e exactly-once"
  - "Agregação entre múltiplos sinks, conversão de unidades e preenchimento de timestamp"
  - "CloudWatch live, FinOps, causalidade, benchmark e validação funcional do consumidor"
unknowns:
  - id: U1
    blocks: [AC2]
    unlock: "Confirmar que batch_id é a identidade comum emitida pelo extrator para sink e progress."
  - id: U2
    blocks: [AC6]
    unlock: "Regenerar referências, surface lock, offline manifest e números correntes depois da mudança de contrato."
change_kinds: [extractor, fixture_corpus, knowledge_doc, tool_or_verb, agent_or_skill, status_numbers]
---

# STREAMING_SINK_SLO_EVALUATION — requisitos
