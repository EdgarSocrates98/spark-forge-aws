---
sdd: 1
feature: STREAMING_SINK_SLO_EVALUATION
phase: build_report
profile: dev
status: done
upstream:
  path: docs/sdd/STREAMING_SINK_SLO_EVALUATION/plan.md
  sha256: "b8c102e8a28b1205a5dddd5c323310fabbd46ac7a43007963b71f9b76179e070"
tasks:
  - id: T1
    status: done
    red: {command: "python -m pytest tests/test_facts_streaming_slo.py::test_evaluates_sink_output_slo tests/test_facts_streaming_slo.py::test_sink_slo_uses_batch_timestamp_and_provenance tests/test_facts_streaming_slo.py::test_sink_slo_unresolved_reasons -q --basetemp=E:\\temp\\sparkforge-sink-sdd-t1", exit: 1}
    green: {command: "python -m pytest tests/test_facts_streaming_slo.py -q --basetemp=E:\\temp\\sparkforge-sink-slo-green2", exit: 0}
  - id: T2
    status: done
    red: {command: "python -m pytest tests/test_analyze_streaming_composition.py::test_sink_slo_cli_and_mcp_envelopes_match -q --basetemp=E:\\temp\\sparkforge-sink-sdd-t2", exit: 1}
    green: {command: "python -m pytest tests/test_analyze_streaming_composition.py::test_sink_slo_cli_and_mcp_envelopes_match -q", exit: 0}
  - id: T3
    status: done
    red: {command: "python -m pytest tests/test_fixtures_golden_streaming_composition.py::test_fixture_goldens -q --basetemp=E:\\temp\\sparkforge-sink-golden-red", exit: 1}
    green: {command: "python -m pytest tests/test_fixtures_golden_streaming_composition.py -q --basetemp=E:\\temp\\sparkforge-sink-golden4", exit: 0}
  - id: T4
    status: done
    red: {command: "python -m pytest tests/test_docs_coverage.py::test_streaming_sink_slo_coverage_mentions_batch_link -q --basetemp=E:\\temp\\sparkforge-sink-sdd-t4", exit: 1}
    green: {command: "python -m pytest tests/test_docs_coverage.py::test_streaming_sink_slo_coverage_mentions_batch_link -q", exit: 0}
  - id: T5
    status: done
    red: {command: "python scripts/sync_skills.py --check; python scripts/check_surface_lock.py", exit: 1}
    green: {command: "python scripts/sync_skills.py --check; python scripts/gen_reference_docs.py --check; python scripts/check_surface_lock.py; python scripts/check_status_numbers.py --strict; python scripts/verify_offline_bundle.py --check", exit: 0}
claims:
  - text: "mode=slo avalia num_output_rows diretamente observado em streaming.progress.sink e liga cada medida ao batch temporal correspondente."
    evidence_ref: "sparkforge/facts/streaming_slo.py; tests/test_facts_streaming_slo.py::test_sink_slo_uses_batch_timestamp_and_provenance"
  - text: "Sink sem batch, unidade incompatível, descrição ambígua ou identidade não encontrada permanece streaming.slo.unresolved."
    evidence_ref: "tests/test_facts_streaming_slo.py::test_sink_slo_unresolved_reasons"
  - text: "CLI, MCP e core preservam o mesmo envelope para SLO de sink sem tool nova."
    evidence_ref: "tests/test_analyze_streaming_composition.py::test_sink_slo_cli_and_mcp_envelopes_match"
  - text: "Goldens met, violated e unresolved cobrem facts, composição e SF-STREAM-011/SF-STREAM-012."
    evidence_ref: "fixtures/streaming_composition/slo_sink_met; fixtures/streaming_composition/slo_sink_violated; fixtures/streaming_composition/slo_sink_unresolved"
  - text: "Knowledge, skill, mirrors, referências, surface lock, offline manifest e números correntes foram reconciliados."
    evidence_ref: "knowledge/streaming-operations.md; skills/analyze-streaming-composition/SKILL.md; docs/surface.lock.json; knowledge/offline-manifest.json"
change_id: null
---

# STREAMING_SINK_SLO_EVALUATION — relatório do build

## Resultado

Build concluído em T1–T5. A implementação permanece offline e determinística:
o compositor reutiliza `mode=slo`, lê `num_output_rows` do sink e usa somente
o `batch_id` e o timestamp do batch correspondente para fechar a janela.

## Decisões e limites preservados

- `source: streaming_sink` mede somente quantidade observada de linhas emitidas;
  não é freshness, latência, disponibilidade, DLQ, replay ou exactly-once.
- `sink_name` seleciona uma descrição declarada; descrições múltiplas sem nome
  produzem `ambiguous_sink`.
- Batch ausente, batch ambíguo, timestamp inválido, métrica ausente, unidade
  incompatível ou janela insuficiente produzem unresolved nomeado.
- Não há agregação entre sinks, preenchimento por ordem do arquivo, relógio do
  compositor, CloudWatch, custo, causalidade, benchmark ou endpoint live.
- A suíte completa não foi executada nesta fase, conforme o escopo solicitado.

## Revisão por tarefa

- **T1:** comparador SLO ganhou aliases de saída, fonte sink, vínculo temporal
  e preservação de evidência; 22 testes verdes no módulo de fatos.
- **T2:** CLI, MCP e core usam o mesmo envelope; paridade verde.
- **T3:** três fixtures cobrem met, violated, unresolved e as regras existentes;
  golden corpus verde.
- **T4:** skill, knowledge, cobertura do prompt e referências geradas descrevem
  a fonte sink e seus limites.
- **T5:** mirrors, referências, surface lock, offline manifest e números foram
  reconciliados.

## Evidência de gates

- 55 testes focados verdes no lote facts/composição/goldens/docs.
- `sparkforge sdd check --repo . --feature STREAMING_SINK_SLO_EVALUATION` verde
  para as fases anteriores.

Não há medição de performance, custo, throughput, latência ou capacidade cloud.
