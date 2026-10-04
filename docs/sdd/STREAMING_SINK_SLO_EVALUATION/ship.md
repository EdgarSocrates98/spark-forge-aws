---
sdd: 1
feature: STREAMING_SINK_SLO_EVALUATION
phase: ship
profile: dev
status: done
upstream:
  path: docs/sdd/STREAMING_SINK_SLO_EVALUATION/build_report.md
  sha256: "e1f04bc2f095798b9d75f4422093c032fb7fec60efe88e6f1c09b9b97b088dec"
hypothesis_outcome: confirmed
registries:
  - reachability_lists
  - fixture_kind_coverage
  - snippet_measure
  - fixture_corpus_gates
  - offline_manifest
  - sources_lock
  - surface_lock
  - generated_reference
  - sync_skills
  - agents_parity
  - status_numbers_gate
deviations:
  - "Reutilizado mode=slo e a tool existente; não foi criado endpoint nem tool nova."
  - "O timestamp do sink é aceito somente quando há vínculo único com streaming.progress.batch pelo batch_id e query_name."
  - "A entrega mede quantidade observada de saída; não fecha freshness, p95, disponibilidade, replay ou exactly-once."
  - "A suíte completa não foi executada, conforme escopo solicitado."
---

# STREAMING_SINK_SLO_EVALUATION — ship

## Resultado

Ship concluído. `mode=slo` agora avalia `num_output_rows` observado em
`streaming.progress.sink`, liga a medida ao timestamp do batch correspondente e
preserva os `fact_id` do sink e do batch no resultado. O caminho continua offline,
determinístico e fail-closed.

## Aceitação

- **AC1–AC3:** aliases de saída, unidade `rows`, identidade `query_name`,
  `batch_id`, `sink_name`, vínculo temporal único, proveniência e unresolved
  nomeado cobertos por `tests/test_facts_streaming_slo.py`.
- **AC4:** core, CLI e MCP preservam o mesmo envelope em
  `test_sink_slo_cli_and_mcp_envelopes_match`.
- **AC5:** goldens `slo_sink_met`, `slo_sink_violated` e `slo_sink_unresolved`
  cobrem avaliação resolvida, violação e blind spots.
- **AC6:** skill canônica, dois mirrors, knowledge, cobertura do prompt,
  referências geradas, surface lock, offline manifest e números correntes foram
  reconciliados.

## Gates executados

- `tests/test_facts_streaming_slo.py`: 22 passed.
- facts/composição/goldens/docs focados: 55 passed.
- `tests/test_fixtures_kind_coverage.py tests/test_verify_wheel.py`: 112 passed.
- `tests/test_sync_render.py tests/test_agent_coverage.py tests/test_docs_coverage.py`: 147 passed.
- `tests/test_agents_parity.py`: 69 passed.
- offline expansion, referências e surface: 16 passed.
- aceitação CLI/MCP + cobertura sink: 2 passed.
- checks de skills, referências, surface lock, status numbers e offline bundle: verdes.
- `sparkforge sdd check --repo . --feature STREAMING_SINK_SLO_EVALUATION`: verde.

## Limites e próximos desbloqueios

Não há medição de performance, custo, throughput, latência, capacidade cloud,
freshness, p95, DLQ, replay, exactly-once ou saúde end-to-end. Para fechar esses
eixos ainda são necessários artefatos temporais pareados, endpoint/collector live
ou execução funcional do runtime, conforme o caso.

O ship não altera a ativação do Decision Plane nem cria claims de produção.
