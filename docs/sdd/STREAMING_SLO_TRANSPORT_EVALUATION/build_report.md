---
sdd: 1
feature: STREAMING_SLO_TRANSPORT_EVALUATION
phase: build_report
profile: dev
status: done
upstream:
  path: docs/sdd/STREAMING_SLO_TRANSPORT_EVALUATION/plan.md
  sha256: "3ca87ffb0216c63c6ca9139af6d66bae3cea3577cf299eaf3c00104e228eb7fd"
tasks:
  - id: T1
    status: done
    red: {command: "python -m pytest tests/test_facts_streaming_slo.py::test_evaluates_transport_slo_by_declared_identity tests/test_facts_streaming_slo.py::test_evaluates_kinesis_iterator_age_and_kafka_lag tests/test_facts_streaming_slo.py::test_transport_slo_unresolved_reasons -q (before transport observation branch)", exit: 1}
    green: {command: "python -m pytest tests/test_facts_streaming_slo.py tests/test_facts_streaming_ops.py tests/test_facts_streaming_composition.py -q", exit: 0}
  - id: T2
    status: done
    red: {command: "python -m pytest tests/test_analyze_streaming_composition.py::test_transport_slo_cli_and_mcp_envelopes_match -q (before transport forwarding)", exit: 1}
    green: {command: "python -m pytest tests/test_analyze_streaming_composition.py::test_transport_slo_cli_and_mcp_envelopes_match -q", exit: 0}
  - id: T3
    status: done
    red: {command: "python -m pytest tests/test_fixtures_golden_streaming_composition.py::test_fixture_goldens -q (transport goldens not yet generated)", exit: 1}
    green: {command: "python -m pytest tests/test_fixtures_golden_streaming_composition.py -q", exit: 0}
  - id: T4
    status: done
    red: {command: "python -m pytest tests/test_docs_coverage.py::test_streaming_transport_slo_coverage_mentions_transport_key -q (coverage entry absent)", exit: 1}
    green: {command: "python -m pytest tests/test_docs_coverage.py::test_streaming_coverage_mentions_slo_evaluation tests/test_docs_coverage.py::test_streaming_transport_slo_coverage_mentions_transport_key tests/test_reference_docs.py tests/test_surface_lock.py -q", exit: 0}
  - id: T5
    status: done
    red: {command: "python scripts/check_surface_lock.py (lock not regenerated)", exit: 1}
    green: {command: "python scripts/check_surface_lock.py; python scripts/check_status_numbers.py --strict; python scripts/verify_offline_bundle.py --check; python scripts/gen_reference_docs.py --check; python scripts/sync_skills.py --check", exit: 0}
claims:
  - text: "mode=slo avalia séries diretamente observadas de kafka.lag e kinesis.shard por transport_key, sem exigir query_name para fontes de transporte."
    evidence_ref: "sparkforge/facts/streaming_slo.py; tests/test_facts_streaming_slo.py"
  - text: "Kafka lag usa records e Kinesis iterator age usa ms; timestamps timezone-aware e cobertura de janela são pré-condições."
    evidence_ref: "sparkforge/facts/streaming_slo.py; sparkforge/facts/transport.py; tests/test_facts_streaming_slo.py"
  - text: "CLI, MCP e core preservam o mesmo envelope e os mesmos source_fact_ids para SLO de transporte."
    evidence_ref: "tests/test_analyze_streaming_composition.py::test_transport_slo_cli_and_mcp_envelopes_match"
  - text: "Goldens Kafka met, Kinesis violated e transport unresolved cobrem fatos, composição e regras existentes."
    evidence_ref: "fixtures/streaming_composition/slo_kafka_met; fixtures/streaming_composition/slo_kinesis_violated; fixtures/streaming_composition/slo_transport_unresolved"
  - text: "Knowledge, skill, mirrors, referências, surface lock, offline manifest e números correntes foram reconciliados."
    evidence_ref: "knowledge/transport-diagnostics.md; skills/analyze-streaming-composition/SKILL.md; docs/surface.lock.json; knowledge/offline-manifest.json"
change_id: null
---

# STREAMING_SLO_TRANSPORT_EVALUATION — relatório do build

## Resultado

Build concluído em T1–T5. A implementação permanece offline e determinística:
o compositor reutiliza `mode=slo` e compara `kafka.lag` ou `kinesis.shard`
somente quando identidade, unidade, timestamp, quantidade e cobertura temporal
são observáveis.

## Decisões e limites preservados

- `source: kafka` lê `lag` em `records` e `source: kinesis` lê
  `iterator_age_ms` em `ms`; não há conversão de unidade.
- `transport_key` é obrigatório para transporte, podendo vir da chamada ou do
  contrato `streaming.slo`; não é inferido por nome de arquivo.
- Só há avaliação com pelo menos duas observações timezone-aware e span igual ou
  maior que a janela. Grupos, topics, streams e shards não são agregados.
- `kinesis.metric` sem timestamp não vira série; CloudWatch, p95, freshness,
  sink health, custo e causalidade permanecem fora do contrato.
- A suíte completa não foi executada nesta fase, conforme o escopo solicitado.

## Revisão por tarefa

- **T1:** comparador de progress foi estendido para Kafka/Kinesis, preservando
  o caminho Structured Streaming, recusando séries misturadas e publicando
  unresolved nomeado; 24 testes verdes.
- **T2:** composição, CLI e MCP encaminham `transport_key` ao mesmo core; teste
  de paridade CLI/MCP verde.
- **T3:** três fixtures novas cobrem met, violated, identidade ausente,
  `source_fact_ids` e `SF-STREAM-011`/`SF-STREAM-012`; golden suite verde.
- **T4:** skill, knowledge, prompt coverage e referências geradas descrevem a
  avaliação de transporte e seus limites.
- **T5:** surface lock, offline manifest, status numbers, referências e mirrors
  foram reconciliados; o script de regeneração ganhou seleção `--only` e passou
  a incluir contratos SLO e argumentos temporais.

## Evidência de gates

- 24 testes focados de fatos/composição/ops.
- 18 testes de paridade e goldens no lote de transporte/SLO.
- 14 testes de docs, referências e surface.
- `check_surface_lock.py`, `check_status_numbers.py --strict`,
  `verify_offline_bundle.py --check`, `gen_reference_docs.py --check` e
  `sync_skills.py --check` verdes.

Não há medição de performance, custo, throughput, latência ou capacidade cloud.
