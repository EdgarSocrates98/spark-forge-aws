---
sdd: 1
feature: STREAMING_PROGRESS_OBSERVABILITY_DEPTH
phase: define
profile: dev
status: ready
upstream:
  path: docs/sdd/STREAMING_PROGRESS_OBSERVABILITY_DEPTH/explore.md
  sha256: "84c1b8706c1375b7c2d23682590ede032e020defc04469816ba561a794d2aa38"
hypothesis:
  claim: "Resumos temporais compactos no fact streaming.progress.series tornam duração, memória do state e watermark reutilizáveis por rules sem abrir novamente o progress bruto."
  prediction: "Uma série com pelo menos dois batches válidos e watermark/state memory observados produz medidas de span, duração e memória, além de watermark_stalled ou state_memory_growth_observed quando aplicável; medidas ausentes ou inválidas permanecem unresolved e não produzem finding falso."
  experiment: "Adicionar testes vermelhos para extração, lacunas temporais, regras e golden; implementar o resumo; regenerar goldens e executar gates focados de fatos, rules, fixtures, wheel e documentação."
acceptance:
  - id: AC1
    statement: "streaming.progress.series resume observed_span_seconds, batch duration e state memory somente quando a série correspondente tem pelo menos duas medidas numéricas válidas."
    verified_by: {kind: test, ref: tests/test_facts_streaming.py::test_progress_series_summarizes_temporal_state_and_watermark}
  - id: AC2
    statement: "Watermark repetido produz watermark_stalled e watermark inválido ou incompleto produz unresolved nomeado sem preencher valor ausente."
    verified_by: {kind: test, ref: tests/test_facts_streaming.py::test_progress_series_unresolved_for_invalid_temporal_measurement}
  - id: AC3
    statement: "As regras SF-STREAM-013 e SF-STREAM-014 exigem série suficiente, runtime observado e flags derivadas; ausência desses requisitos não gera finding."
    verified_by: {kind: test, ref: tests/test_streaming_rules.py::test_progress_observability_depth_rules_are_evidence_first}
  - id: AC4
    statement: "Goldens positivos, divergentes e insuficientes preservam facts determinísticos e cobrem watermark parado, memória crescente e unresolved."
    verified_by: {kind: test, ref: tests/test_fixtures_golden_streaming.py::TestGolden::test_facts_match_golden}
  - id: AC5
    statement: "Rules novas permanecem alcançáveis pelo catálogo e todos os findings derivados continuam válidos pelo schema."
    verified_by: {kind: test, ref: tests/test_streaming_rules.py::test_progress_observability_depth_rules_are_evidence_first}
  - id: AC6
    statement: "Knowledge, skill, prompt coverage, referências e números correntes descrevem os resumos e seus limites sem claim de causa ou performance."
    verified_by: {kind: command, ref: python scripts/check_status_numbers.py --strict}
success:
  - id: SC1
    metric: "AC1–AC6 verdes e nenhum novo resumo transforma ausência de métrica em zero ou finding"
    source: "pytest focado, goldens, catálogo, gates de skills/referências/status e bundle offline"
out_of_scope:
  - "Freshness, p95, percentile, tendência estatística longa, causalidade, custo ou benchmark"
  - "Leitura de arquivos internos de checkpoint sem formato/version guard"
  - "CloudWatch/live collector, replay Spark e validação funcional do sink"
  - "Threshold fixo para batch duration, state memory ou watermark"
unknowns:
  - id: U1
    blocks: [AC1, AC2]
    unlock: "Confirmar que timestamps e eventTime.watermark do progress são strings ISO timezone-aware no corpus de fixtures; valores que não forem ficam unresolved."
  - id: U2
    blocks: [AC6]
    unlock: "Regenerar referências, surface/manifest quando aplicável e números correntes após a alteração do extrator e catálogo."
change_kinds: [extractor, rule, rule_runtime_scope, fixture_corpus, knowledge_doc, agent_or_skill, status_numbers]
---

# STREAMING_PROGRESS_OBSERVABILITY_DEPTH — requisitos
