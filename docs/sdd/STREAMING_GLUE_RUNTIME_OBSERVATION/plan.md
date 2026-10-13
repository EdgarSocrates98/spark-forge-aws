---
sdd: 1
feature: STREAMING_GLUE_RUNTIME_OBSERVATION
phase: plan
profile: dev
status: ready
upstream:
  path: docs/sdd/STREAMING_GLUE_RUNTIME_OBSERVATION/design.md
  sha256: "4d760ab0486c0e65a11ae3bb9e753354abdbf5bb3be811321ef17ee384648c12"
tasks:
  - id: T1
    files: [sparkforge_aws/facts/glue_streaming.py, sparkforge_aws/facts/streaming_glue_runtime.py, tests/test_streaming_glue_runtime_observation.py]
    covers: [AC1, AC2, AC3]
    test: {path: tests/test_streaming_glue_runtime_observation.py, name: test_runtime_link_matches_literal_job_and_preserves_sources}
  - id: T2
    files: [sparkforge_aws/facts/fusion.py, tests/test_streaming_glue_runtime_observation.py]
    covers: [AC4]
    test: {path: tests/test_streaming_glue_runtime_observation.py, name: test_fuse_runtime_observation_is_guarded_and_idempotent}
  - id: T3
    files: [rules/catalog/glue-streaming.yaml, tests/test_streaming_glue_runtime_observation.py]
    covers: [AC5]
    test: {path: tests/test_streaming_glue_runtime_observation.py, name: test_runtime_observation_rules_are_evidence_backed}
  - id: T4
    files: [fixtures/streaming_glue_runtime_observation, scripts/regen_streaming_glue_runtime_observation.py, tests/test_streaming_glue_runtime_observation.py, tests/test_fixtures_golden_streaming_glue_runtime_observation.py]
    covers: [AC2, AC3, AC5]
    test: {path: tests/test_streaming_glue_runtime_observation.py, name: test_fixture_goldens_cover_consistent_drift_and_unresolved}
  - id: T5
    files: [knowledge/glue-streaming-rtm.md, skills/review-glue-streaming/SKILL.md, docs/streaming/prompt-coverage.md, tests/test_docs_coverage.py]
    covers: [AC6]
    test: {path: tests/test_docs_coverage.py, name: test_streaming_glue_runtime_observation_coverage}
---

# STREAMING_GLUE_RUNTIME_OBSERVATION — plano

Implementação serializada: primeiro preservar os campos efetivos e criar o
compositor com testes vermelhos; depois conectar ao `fuse`; em seguida adicionar
rules/goldens; por fim atualizar workflow, knowledge, referências, mirrors,
locks e números. Não criar verbo CLI/MCP novo.

## T1 — facts e composição pura

Escrever testes que montam `Fact` de definição e runs terminais, cobrindo match
literal, múltiplos jobs, run sem campo e `source_fact_ids`. Implementar
`streaming_glue_runtime.py` sem leitura de arquivo. Estender
`glue_streaming.py` somente para `worker_type` e normalização necessária.

## T2 — integração guarded no fuse

Invocar o builder somente quando houver `glue.streaming.job` e
`glue.job_run`/`glue.job_run.analyzed`. Testar que pool sem os dois lados é
byte a byte igual e que `fuse(fuse(facts))` não duplica link.

## T3 — regras evidence-first

Adicionar `SF-GLUESTREAM-006` para `divergence_count > 0` e
`SF-GLUESTREAM-007` para `glue.streaming.runtime.unresolved`, ambos com
`runtime_scope: {}`, action fechado, fonte oficial e rollback.

## T4 — corpus

Criar três cenários: versão/capacidade consistente; versão/worker drift; e
identidade/campo ausente. Gerar fatos e findings pelos mesmos builders usados
no produto, registrar o golden module e os dois inventários manuais.

## T5 — documentação

Documentar comandos existentes (`analyze glue-streaming`, `analyze glue-job-runs`,
`fuse`, `judge`), limits e caminho de reextração. Rodar geradores oficiais e
gates derivados; não declarar saúde, latência ou ganho sem medida.
