---
sdd: 1
feature: STREAMING_FLINK_TEMPORAL_METRICS
phase: define
profile: dev
status: ready
upstream:
  path: docs/sdd/STREAMING_FLINK_TEMPORAL_METRICS/explore.md
  sha256: "e5f2b3f787dbe0a1502e225d8a01c18d77364fc2052b91388855d94af3cbed1c"
hypothesis:
  claim: "Um artifact offline de Apache Flink com pontos temporais explícitos pode preservar métricas upstream como facts observacionais sem misturar Managed Flink ou inferir saúde."
  prediction: "Registros com nome, valor numérico e timestamp textual produzem flink.metric com metadata escalar e observed_at; campos obrigatórios ausentes ou inválidos produzem flink.unresolved sem fact parcial; artifacts antigos sem metrics mantêm o contrato anterior."
  experiment: "Adicionar testes unitários e golden upstream, executar o extrator offline e os gates de fixtures, skills, referências, surface, knowledge e status."
acceptance:
  - id: AC1
    statement: "O extrator upstream preserva cada observação temporal válida como flink.metric com name, value numérico, observed_at e metadata escalar explícita, descartando estruturas aninhadas."
    verified_by: {kind: test, ref: "tests/test_facts_flink.py::test_flink_temporal_metrics_preserve_observed_value_and_metadata"}
  - id: AC2
    statement: "Métrica sem timestamp textual, nome ou valor numérico não gera fact parcial e publica flink.unresolved com razão nomeada, sem inferir unidade ou epoch numérico."
    verified_by: {kind: test, ref: "tests/test_facts_flink.py::test_flink_temporal_metric_missing_timestamp_is_unresolved"}
  - id: AC3
    statement: "Shape inválido do bloco metrics ou registro inválido permanece unresolved e não é convertido em zero ou métrica sintética."
    verified_by: {kind: test, ref: "tests/test_facts_flink.py::test_flink_temporal_metrics_invalid_shape_is_unresolved"}
  - id: AC4
    statement: "O corpus golden Flink exercita flink.metric, unresolved temporal e determinismo sem alterar o namespace Managed Flink."
    verified_by: {kind: test, ref: "tests/test_fixtures_golden_flink.py::test_flink_fixture_corpus_is_complete"}
  - id: AC5
    statement: "Skill, knowledge, cobertura, referências geradas, mirrors, locks, manifesto offline e números correntes descrevem o contrato e passam nos gates distribuídos."
    verified_by: {kind: command, ref: "python scripts/sync_skills.py --check && python scripts/gen_reference_docs.py --check && python scripts/check_surface_lock.py && python scripts/check_status_numbers.py --strict && python scripts/verify_offline_bundle.py --check"}
  - id: AC6
    statement: "Artifacts upstream legados sem a chave metrics continuam emitindo os mesmos kinds observacionais existentes."
    guard: "A guarda passa antes e depois por desenho para impedir que o novo contrato recuse artifacts históricos sem bloco temporal."
    verified_by: {kind: test, ref: "tests/test_facts_flink.py::test_flink_dump_emits_job_operator_checkpoint_state"}
success:
  - id: SC1
    metric: "AC1–AC6 verdes, com flink.metric apenas para observações upstream válidas e unresolved para blind spots nomeados"
    source: "testes unitários/golden e gates documentais executados no repositório"
out_of_scope:
  - "collector live Flink REST, métricas de broker ou aquisição AWS"
  - "savepoints, job graph, replay, benchmark e validação funcional"
  - "health, SLO, tendência, causalidade, custo ou threshold derivados de um ponto isolado"
  - "Managed Flink: seu namespace e contrato temporal permanecem inalterados"
  - "nova tool MCP, novo verbo CLI ou chamada a provider"
unknowns:
  - id: U1
    blocks: [AC4]
    unlock: "Criar fixture upstream temporal, regenerar facts/findings golden e executar o corpus Flink."
case_id: null
change_kinds: [extractor, fixture_corpus, knowledge_doc, agent_or_skill, tool_or_verb, status_numbers]
---

# STREAMING_FLINK_TEMPORAL_METRICS — requisitos

O analyzer continua offline e evidence-first. `flink.metric` é observação de
artifact upstream; julgamento temporal, saúde e tendência exigem composição e
série comparável posterior.
