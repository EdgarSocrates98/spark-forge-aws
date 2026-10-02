---
sdd: 1
feature: STREAMING_SLO_EVALUATION
phase: define
profile: dev
status: ready
upstream:
  path: docs/sdd/STREAMING_SLO_EVALUATION/explore.md
  sha256: "1450a424f47197a55abd703dbb563246ab515f981f2a144e3db5e4825af32c01"
hypothesis:
  claim: "Uma composição evidence-first consegue avaliar SLOs de streaming declarados quando há batches Structured Streaming com métrica, timestamp, query e janela compatíveis."
  prediction: "Uma série com pelo menos duas observações, span igual ou maior que a janela e unidade compatível produz status met ou violated; declaração, identidade, métrica, unidade ou cobertura ausente produz somente streaming.slo.unresolved e finding estrutural."
  experiment: "Extrair contrato e progress JSONL, compor mode=slo com query e nome declarados, julgar os goldens met/violated/unresolved e comparar envelopes CLI/MCP."
acceptance:
  - id: AC1
    statement: "A composição seleciona exatamente um streaming.slo por nome ou por unicidade, exige query_name, aceita somente métricas diretamente observadas em streaming.progress.batch, valida unidade e preserva source_fact_ids."
    verified_by: {kind: test, ref: tests/test_facts_streaming_slo.py::test_evaluates_direct_progress_metric}
  - id: AC2
    statement: "O compositor calcula observed_min, observed_max, observation_count e observed_span_seconds e só produz met/violated quando a janela declarada foi coberta; o comparador suporta lt, lte, gt, gte e eq."
    verified_by: {kind: test, ref: tests/test_facts_streaming_slo.py::test_slo_status_and_window_coverage}
  - id: AC3
    statement: "Falta de SLO, query, métrica, unidade, operador, janela, source compatível, observações suficientes ou cobertura temporal produz unresolved nomeado e nunca status met por ausência de evidência."
    verified_by: {kind: test, ref: tests/test_facts_streaming_slo.py::test_slo_unresolved_reasons}
  - id: AC4
    statement: "SF-STREAM-010 julga somente streaming.slo.evaluation com status violated, e SF-STREAM-011 nomeia streaming.slo.unresolved; ambos preservam evidence e não atribuem causalidade ou custo."
    verified_by: {kind: test, ref: tests/test_streaming_rules.py::test_slo_evaluation_rules_are_evidence_first}
  - id: AC5
    statement: "CLI e MCP expõem mode=slo, slo_name e query_name pelo mesmo core read-only, com envelope e detail_level compatíveis."
    verified_by: {kind: test, ref: tests/test_analyze_streaming_composition.py::test_slo_cli_and_mcp_envelopes_match}
  - id: AC6
    statement: "Goldens met, violated e unresolved cobrem os novos kinds, a regra positiva, a regra estrutural e a regressão dos modos existentes."
    verified_by: {kind: test, ref: tests/test_fixtures_golden_streaming_composition.py::test_fixture_goldens}
  - id: AC7
    statement: "Knowledge, prompt coverage, skill, referências geradas, surface lock, bundle offline, números correntes e SDD registram avaliação observada e seus limites."
    verified_by: {kind: command, ref: python scripts/sync_skills.py --check}
success:
  - id: SC1
    metric: "Todos AC1–AC7 verdes; série compatível separa met, violated e unresolved sem inferir sucesso, causa ou economia."
    source: "pytest focalizado, goldens, judge, CLI/MCP e gates do catálogo, surface, documentação e bundle offline"
out_of_scope:
  - "Collectors live de CloudWatch, Kafka, Kinesis, Spark ou Glue"
  - "Inferência de p95, freshness, disponibilidade, RPO, RTO ou exatamente-once"
  - "Conversão de unidades, agregação estatística não observada ou preenchimento de valores ausentes"
  - "FinOps, atribuição de custo, causalidade e benchmark de performance"
unknowns:
  - id: U1
    blocks: [AC1, AC2]
    unlock: "Confirmar no extractor streaming.py os nomes de measures e a forma de timestamp dos batches antes de implementar o compositor."
  - id: U2
    blocks: [AC7]
    unlock: "Regenerar referências, surface lock, offline manifest e status numbers depois que o modo e os kinds existirem."
change_kinds: [extractor, fixture_corpus, knowledge_doc, tool_or_verb, rule, agent_or_skill, status_numbers]
---

# STREAMING_SLO_EVALUATION — requisitos

Esta feature transforma declaração em avaliação somente quando observação,
identidade e janela estão presentes. O resultado não substitui o contrato SLO:
ele o referencia por `source_fact_ids` e conserva `causal_inference: false`.
