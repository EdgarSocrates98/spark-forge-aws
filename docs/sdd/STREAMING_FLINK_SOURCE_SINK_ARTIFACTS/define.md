---
sdd: 1
feature: STREAMING_FLINK_SOURCE_SINK_ARTIFACTS
phase: define
profile: dev
status: ready
upstream:
  path: docs/sdd/STREAMING_FLINK_SOURCE_SINK_ARTIFACTS/explore.md
  sha256: "b0d93fe5193e2b3807228fd99cfbd70fdd9be1efe8278b31aef71ac5ff046bf1"
hypothesis:
  claim: "Facts explícitos de source e sink tornam métricas de entrada/saída auditáveis e deixam a ausência de observabilidade nomeada, sem misturar Apache Flink com Managed Flink."
  prediction: "Um dump com sources/sinks produzirá facts com identidade, connector e medidas somente observadas; um dump sem esses blocos produzirá unresolved source_metrics_missing e sink_metrics_missing; nenhum campo ausente será convertido em zero."
  experiment: "Executar testes unitários, corpus golden Flink, validação de facts, reachability de kinds e gates de sincronização documental."
acceptance:
  - id: AC1
    statement: "O extrator Apache Flink emite flink.source e flink.sink para registros objeto ou lista, com aliases de identidade e métricas numéricas observadas."
    verified_by: {kind: test, ref: "tests/test_facts_flink.py::test_flink_dump_emits_explicit_source_and_sink"}
  - id: AC2
    statement: "Source e sink preservam connector, delivery semantics e outros atributos escalares sem importar estruturas aninhadas."
    verified_by: {kind: test, ref: "tests/test_facts_flink.py::test_flink_source_sink_preserve_observed_fields_only"}
  - id: AC3
    statement: "Ausência, formato inválido ou registro sem campos de source/sink emite flink.unresolved com razão nomeada e não emite fact vazio."
    verified_by: {kind: test, ref: "tests/test_facts_flink.py::test_flink_source_sink_absence_is_unresolved"}
  - id: AC4
    statement: "O namespace managed_flink permanece inalterado e nenhum fact flink.source/flink.sink é emitido para artifact managed_flink."
    verified_by: {kind: test, ref: "tests/test_facts_flink.py::test_managed_flink_dump_keeps_service_namespace"}
  - id: AC5
    statement: "O corpus golden cobre os novos kinds, findings existentes permanecem evidence-backed e os fatos regenerados são determinísticos."
    verified_by: {kind: test, ref: "tests/test_fixtures_golden_flink.py::test_flink_fixture_corpus_is_complete"}
  - id: AC6
    statement: "Skill, knowledge, prompt coverage, referências e mirrors registram os facts e limites sem criar surface nova."
    verified_by: {kind: test, ref: "tests/test_docs_coverage.py::test_flink_source_sink_artifacts_coverage"}
success:
  - id: SC1
    metric: "Dumps com endpoints explícitos preservam source/sink como fatos independentes"
    source: "tests/test_facts_flink.py::test_flink_dump_emits_explicit_source_and_sink"
  - id: SC2
    metric: "Corpus Flink com kinds declarados cobertos por golden"
    source: "tests/test_fixtures_golden_flink.py::test_flink_fixture_corpus_is_complete"
  - id: SC3
    metric: "Surface delta de CLI/MCP"
    source: "docs/surface.lock.json e teste de paridade de superfície"
out_of_scope:
  - "Consulta live, CloudWatch temporal, savepoints, replay e execução de jobs."
  - "Inferência de exactly-once, throughput temporal, causa raiz ou capacidade adequada."
  - "Managed Flink, novos verbos CLI e nova ferramenta MCP."
unknowns:
  - id: U1
    blocks: [AC1, AC2]
    unlock: "Dumps reais com schema específico de connector e nomes alternativos; esta wave suporta somente aliases declarados no contrato offline."
  - id: U2
    blocks: [AC3]
    unlock: "Definição do produtor sobre se ausência de source/sink significa endpoint inexistente ou apenas métrica não coletada; o contrato registra ambos como unresolved, sem inferência."
case_id: null
change_kinds: [extractor, fixture_corpus, knowledge_doc, agent_or_skill, status_numbers]
---

# STREAMING_FLINK_SOURCE_SINK_ARTIFACTS — requisitos

## Problema

O dump Flink atual reconhece operadores e métricas de checkpoint/state, mas não
oferece um fato independente para os endpoints do pipeline. Uma source pode
ter lag/backlog e um sink pode ter commits pendentes sem que isso seja
distinguível de um operador genérico; quando os endpoints não são coletados, o
motor também precisa expor a lacuna em vez de preenchê-la.

## Critério de evidência

`flink.source` e `flink.sink` carregam apenas campos escalares e numéricos
presentes no registro original, com provenance e fact id normais. Campos
ausentes não viram zero. `flink.unresolved` registra o motivo da ausência ou
formato inválido; não há finding novo nesta wave sem uma regra que estabeleça
um limiar observável.
