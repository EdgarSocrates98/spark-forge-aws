---
sdd: 1
feature: STREAMING_PROGRESS_OBSERVABILITY_DEPTH
phase: build_report
profile: dev
status: done
upstream:
  path: docs/sdd/STREAMING_PROGRESS_OBSERVABILITY_DEPTH/plan.md
  sha256: "e64ef0165878829893dab41d65ffaabf4628a1b5f1673e883e3ce266999e8003"
tasks:
  - id: T1
    status: done
    red: {command: "python -m pytest tests/test_facts_streaming.py::test_progress_series_summarizes_temporal_state_and_watermark tests/test_facts_streaming.py::test_progress_series_unresolved_for_invalid_temporal_measurement -q --basetemp=E:\\temp\\sparkforge-progress-depth-t1", exit: 1}
    green: {command: "python -m pytest tests/test_facts_streaming.py::test_progress_series_summarizes_temporal_state_and_watermark tests/test_facts_streaming.py::test_progress_series_unresolved_for_invalid_temporal_measurement -q --basetemp=E:\\temp\\sparkforge-progress-depth-t1-green", exit: 0}
  - id: T2
    status: done
    red: {command: "python -m pytest tests/test_streaming_rules.py::test_progress_observability_depth_rules_are_evidence_first -q --basetemp=E:\\temp\\sparkforge-progress-depth-t2", exit: 1}
    green: {command: "python -m pytest tests/test_streaming_rules.py::test_progress_observability_depth_rules_are_evidence_first -q --basetemp=E:\\temp\\sparkforge-progress-depth-t2-green", exit: 0}
  - id: T3
    status: done
    red: {command: "python -m pytest tests/test_fixtures_golden_streaming.py::TestGolden::test_facts_match_golden -q --basetemp=E:\\temp\\sparkforge-progress-depth-t3", exit: 1}
    green: {command: "python -m pytest tests/test_fixtures_golden_streaming.py -q --basetemp=E:\\temp\\sparkforge-progress-depth-golden-green", exit: 0}
  - id: T4
    status: done
    red: {command: "python -m pytest tests/test_docs_coverage.py::test_streaming_progress_observability_depth_coverage -q --basetemp=E:\\temp\\sparkforge-progress-depth-t4", exit: 1}
    green: {command: "python -m pytest tests/test_docs_coverage.py::test_streaming_progress_observability_depth_coverage -q --basetemp=E:\\temp\\sparkforge-progress-depth-t4-green", exit: 0}
claims:
  - text: "streaming.progress.series resume span temporal, duração de batch, memória agregada do state e watermark somente quando as medidas observadas são completas."
    evidence_ref: "sparkforge/facts/streaming.py; tests/test_facts_streaming.py::test_progress_series_summarizes_temporal_state_and_watermark"
  - text: "Watermark inválido ou série temporal incompleta permanece unresolved nomeado; o extrator não usa ordem do arquivo para preencher a lacuna."
    evidence_ref: "tests/test_facts_streaming.py::test_progress_series_unresolved_for_invalid_temporal_measurement"
  - text: "SF-STREAM-013 e SF-STREAM-014 exigem série com duas observações e runtime evidence antes de julgar sintomas de watermark parado ou memória crescente."
    evidence_ref: "rules/catalog/streaming.yaml; tests/test_streaming_rules.py::test_progress_observability_depth_rules_are_evidence_first"
  - text: "Fixture positiva, runtime divergente e nova fixture de watermark parado permanecem determinísticas e cobrem facts/findings/gates."
    evidence_ref: "fixtures/streaming/progress_watermark_stalled; tests/test_fixtures_golden_streaming.py::TestGolden::test_facts_match_golden"
  - text: "Knowledge, skill, mirrors, referências, surface lock, offline manifest e números correntes foram reconciliados."
    evidence_ref: "knowledge/streaming-reliability.md; skills/review-structured-streaming/SKILL.md; docs/surface.lock.json; knowledge/offline-manifest.json"
change_id: null
---

# STREAMING_PROGRESS_OBSERVABILITY_DEPTH — relatório do build

## Resultado

Build concluído em T1–T4. O extrator mantém `streaming.progress.series` como
envelope compacto e determinístico: não reemite cada batch nem cria um segundo
namespace para a mesma evidência. Quando há pelo menos duas observações válidas,
resume span temporal, duração, estado, memória agregada e watermark conforme a
medida disponível; lacunas permanecem nomeadas como `unresolved`.

## Decisões e limites preservados

- `watermark_stalled` é sintoma de igualdade dos watermarks observados; não é
  freshness, atraso de negócio, causa raiz ou prova de falha de processamento.
- `state_memory_growth_observed` mede crescimento do total observado por batch;
  não é leak, OOM, pressão de heap ou atribuição causal.
- Timestamps e watermarks precisam ser ISO 8601 timezone-aware; valores inválidos
  não são ordenados pelo arquivo nem convertidos por relógio local.
- As regras novas exigem runtime evidence e duas observações; não há threshold
  inventado, benchmark, custo, exactly-once, replay, endpoint live ou claim de
  performance.
- A suíte completa não foi executada nesta frente; foram executados lotes focados
  e gates derivados da mudança.

## Revisão por tarefa

- **T1:** medidas temporais, duração, state memory e watermark foram adicionados
  ao resumo; 2 testes direcionados verdes, incluindo unresolved temporal.
- **T2:** `SF-STREAM-013` e `SF-STREAM-014` foram adicionadas com evidence/runtime
  gates; teste de regras evidence-first verde.
- **T3:** fixtures positivas existentes foram regeneradas e a fixture
  `progress_watermark_stalled` cobre os dois novos achados; golden streaming verde.
- **T4:** knowledge, skill, mirrors, prompt coverage, referências, manifestos,
  surface lock, status numbers e gates de catálogo foram reconciliados.

## Evidência de gates

- Facts direcionados: 2 passed; regras direcionadas: 1 passed; cobertura docs: 1
  passed; regressão facts/regras: 11 passed.
- Golden streaming: 35 passed; corpus/fixture/offline gates: 116 passed;
  runtime-scope gates: 781 passed.
- Catálogo/docs/knowledge: primeiro lote identificou e corrigiu `rule_count` e
  fronteiras de mutação; lote completo final passou com 1214 testes.
- `gen_reference_docs --check`, `sync_skills --check`, surface lock, status
  numbers, refresh knowledge offline e bundle offline estão verdes.

Não há medição de performance, custo, throughput, latência, capacidade cloud,
freshness, exatamente-once ou causalidade.
