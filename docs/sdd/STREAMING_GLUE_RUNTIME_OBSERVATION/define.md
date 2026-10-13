---
sdd: 1
feature: STREAMING_GLUE_RUNTIME_OBSERVATION
phase: define
profile: dev
status: ready
upstream:
  path: docs/sdd/STREAMING_GLUE_RUNTIME_OBSERVATION/explore.md
  sha256: "67206bc7f480fb9452e607a9f865ac68d35caa5e51f85df44ffa5bf1a3bf27f7"
hypothesis:
  claim: "Correlacionar a definição efetiva Glue Streaming com facts de runs terminais torna versão e capacidade observadas auditáveis sem misturar ausência de run com consistência."
  prediction: "Os goldens consistente, drift e unresolved produzirão respectivamente link sem finding, finding de drift e finding de lacuna; todos preservarão source_fact_ids e nenhum pool sem os dois lados ganhará facts derivados."
  experiment: "Rodar testes unitários, goldens, fuse idempotente e rules reachability sobre facts efetivos e glue.job_run existentes."
acceptance:
  - id: AC1
    statement: "O fact de Glue Streaming preserva worker_type e worker_count quando o dump efetivo os traz, sem preencher campo ausente."
    verified_by: {kind: test, ref: "tests/test_streaming_glue_runtime_observation.py::test_effective_glue_fact_preserves_runtime_capacity_fields"}
  - id: AC2
    statement: "A composição liga somente um job Glue Streaming a runs pelo nome literal único e emite runtime_link com versões, capacidade, estados e source_fact_ids."
    verified_by: {kind: test, ref: "tests/test_streaming_glue_runtime_observation.py::test_runtime_link_matches_literal_job_and_preserves_sources"}
  - id: AC3
    statement: "A composição separa consistent, divergent e unresolved para drift, amostra ausente, identidade ambígua e campo observado ausente."
    verified_by: {kind: test, ref: "tests/test_streaming_glue_runtime_observation.py::test_fixture_goldens_cover_consistent_drift_and_unresolved"}
  - id: AC4
    statement: "O fuse só deriva runtime facts quando há evidência dos dois lados e permanece idempotente."
    verified_by: {kind: test, ref: "tests/test_streaming_glue_runtime_observation.py::test_fuse_runtime_observation_is_guarded_and_idempotent"}
  - id: AC5
    statement: "Drift e runtime não resolvido chegam ao catálogo com evidence, rule_id e severidade P1."
    verified_by: {kind: test, ref: "tests/test_streaming_glue_runtime_observation.py::test_runtime_observation_rules_are_evidence_backed"}
  - id: AC6
    statement: "Knowledge, skill, prompt coverage, generated references e mirrors documentam o fluxo sem criar nova tool ou verbo."
    verified_by: {kind: test, ref: "tests/test_docs_coverage.py::test_streaming_glue_runtime_observation_coverage"}
success:
  - id: SC1
    metric: "Novos fatos derivados de runtime preservando rastreabilidade"
    source: "tests/test_streaming_glue_runtime_observation.py::test_runtime_link_matches_literal_job_and_preserves_sources"
  - id: SC2
    metric: "Surface delta de CLI/MCP"
    source: "docs/surface.lock.json e teste de paridade de superfície"
  - id: SC3
    metric: "Corpus com três estados operacionais"
    source: "fixtures/streaming_glue_runtime_observation e test_fixture_goldens_cover_consistent_drift_and_unresolved"
out_of_scope:
  - "Consulta AWS live, execução Glue, CloudWatch temporal e runtime driver/executor."
  - "Fonte/sink, throughput, latência, backlog, checkpoint e validação funcional."
  - "Interpolação Terraform ou inferência de capacidade a partir de worker type."
  - "Novo verbo CLI ou nova ferramenta MCP."
unknowns:
  - id: U1
    blocks: [AC2, AC3]
    unlock: "Facts de glue.job_run e fixture com nome literal único, nome ausente e nomes ambíguos."
  - id: U2
    blocks: [AC3]
    unlock: "Run sem GlueVersion, WorkerType ou NumberOfWorkers deve emitir campo unresolved nomeado."
case_id: null
change_kinds: [extractor, rule, rule_runtime_scope, fixture_corpus, knowledge_doc, agent_or_skill, status_numbers]
---

# STREAMING_GLUE_RUNTIME_OBSERVATION — requisitos

## Problema

O SparkForge já extrai configuração efetiva de Glue Streaming e histórico
terminal de runs Glue, mas `judge` recebe esses facts separados. Sem um link
determinístico, drift entre versão/capacidade declarada e observada fica
silencioso ou exige leitura manual de dois artefatos.

## Critério de evidência

O runtime observado é somente o que aparece em `glue.job_run`: versão Glue,
worker type, quantidade de workers, estado, duração e identificador do run. O
link nunca trata ausência de run ou campo ausente como igualdade. Cada finding
deve citar o `fact_id` do link derivado, e o link deve apontar para os facts de
origem em `source_fact_ids`.
