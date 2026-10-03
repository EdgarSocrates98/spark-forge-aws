---
sdd: 1
feature: STREAMING_GLUE_SOURCE_SINK_ARTIFACTS
phase: define
profile: dev
status: ready
upstream:
  path: docs/sdd/STREAMING_GLUE_SOURCE_SINK_ARTIFACTS/explore.md
  sha256: "74b33c41709ec07a9861d82ac4c35fce9b9a8f7e4001c8a4a1b58f9dff2e5c97"
hypothesis:
  claim: "Facts explícitos de source e sink tornam endpoints Glue Streaming auditáveis e nomeiam o blind spot quando o dump não contém métricas específicas."
  prediction: "Um dump com sources/sinks produzirá facts independentes com atributos escalares e medidas numéricas presentes; ausência ou formato inválido produzirá unresolved sem converter campos ausentes em zero."
  experiment: "Executar testes unitários, corpus golden Glue Streaming, validação de facts, reachability de kinds e gates documentais."
acceptance:
  - id: AC1
    statement: "O extrator Glue Streaming emite glue.streaming.source e glue.streaming.sink para registros objeto ou lista sob stream, com aliases declarados e medidas numéricas observadas."
    verified_by: {kind: test, ref: "tests/test_facts_glue_streaming.py::test_stream_endpoints_emit_explicit_facts"}
  - id: AC2
    statement: "Source e sink preservam apenas atributos escalares permitidos e não copiam estruturas aninhadas."
    verified_by: {kind: test, ref: "tests/test_facts_glue_streaming.py::test_stream_endpoints_preserve_observed_fields_only"}
  - id: AC3
    statement: "Endpoint ausente, formato inválido, registro inválido ou sem campos úteis emite glue.streaming.unresolved com razão nomeada."
    verified_by: {kind: test, ref: "tests/test_facts_glue_streaming.py::test_stream_endpoint_absence_is_unresolved"}
  - id: AC4
    statement: "O corpus golden cobre os novos kinds e mantém findings existentes evidence-backed e determinísticos."
    verified_by: {kind: test, ref: "tests/test_fixtures_golden_glue_streaming.py::test_glue_streaming_fixture_corpus_is_complete"}
  - id: AC5
    statement: "Skill, knowledge, guias, prompt coverage e SDD registram o contrato e seus limites sem criar surface nova."
    verified_by: {kind: test, ref: "tests/test_docs_coverage.py::test_glue_source_sink_artifacts_coverage"}
success:
  - id: SC1
    metric: "Endpoints declarados aparecem como facts independentes"
    source: "tests/test_facts_glue_streaming.py::test_stream_endpoints_emit_explicit_facts"
  - id: SC2
    metric: "Corpus Glue Streaming com kinds declarados permanece coberto"
    source: "tests/test_fixtures_golden_glue_streaming.py::test_glue_streaming_fixture_corpus_is_complete"
  - id: SC3
    metric: "Surface delta de CLI/MCP"
    source: "docs/surface.lock.json e teste de paridade de superfície"
out_of_scope:
  - "Collector live de Glue/Kafka/Kinesis/CloudWatch."
  - "Métricas temporais, latência end-to-end, throughput, replay e benchmark."
  - "Regra de saúde, capacidade ou semântica exactly-once baseada em endpoint isolado."
  - "Validação funcional e cross-artifact novo."
unknowns:
  - id: U1
    blocks: [AC1, AC2]
    unlock: "Dumps reais com schema distinto de stream.sources/source e stream.sinks/sink; a wave suporta apenas aliases explicitamente documentados."
  - id: U2
    blocks: [AC3]
    unlock: "Definição do produtor sobre endpoint ausente versus métrica não coletada; o contrato permanece unresolved sem escolher entre os dois."
case_id: null
change_kinds: [extractor, fixture_corpus, knowledge_doc, agent_or_skill, status_numbers]
---

# STREAMING_GLUE_SOURCE_SINK_ARTIFACTS — requisitos

## Problema

`glue.streaming.job.attrs.source_type` identifica uma configuração agregada,
mas não preserva source/sink nomeados, connector ou medidas do endpoint. O
analyzer precisa separar declaração do job de evidência de endpoint e expor
ausência em vez de produzir uma falsa observação completa.

## Critério de evidência

`glue.streaming.source` e `glue.streaming.sink` carregam provenance normal,
atributos escalares permitidos e medidas numéricas presentes. `unresolved`
nomeia ausência, formato inválido ou registro sem campos úteis. Nenhuma métrica
ausente vira zero.
