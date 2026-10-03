---
sdd: 1
feature: STREAMING_END_TO_END_PIPELINE
phase: plan
profile: dev
status: ready
upstream:
  path: docs/sdd/STREAMING_END_TO_END_PIPELINE/design.md
  sha256: "02dd1505e5bfbca84a9ed161e3f02cbce63b2f82619f76b39083b340d408c9d1"
tasks:
  - id: T1
    files: [tests/test_streaming_pipeline.py, sparkforge/facts/streaming_pipeline.py]
    covers: [AC1, AC2]
    test: {path: tests/test_streaming_pipeline.py, name: test_pipeline_contract_emits_verified_nodes_and_edges}
  - id: T2
    files: [sparkforge/facts/streaming_composition.py, rules/catalog/streaming.yaml, tests/test_streaming_pipeline.py]
    covers: [AC3]
    test: {path: tests/test_streaming_pipeline.py, name: test_pipeline_rule_fires_only_for_observed_blind_spot}
  - id: T3
    files: [sparkforge/adapters/_core.py, sparkforge/adapters/cli.py, sparkforge/adapters/tools.py, tests/test_streaming_pipeline.py]
    covers: [AC4]
    test: {path: tests/test_streaming_pipeline.py, name: test_pipeline_cli_mcp_envelopes_match}
  - id: T4
    files: [tests/test_fixtures_golden_streaming_pipeline.py, fixtures/streaming_pipeline]
    covers: [AC5]
    test: {path: tests/test_fixtures_golden_streaming_pipeline.py, name: test_streaming_pipeline_fixture_corpus_is_complete}
  - id: T5
    files: [knowledge/streaming-pipeline-diagnostics.md, knowledge/INDEX.md, skills/review-streaming-operations/SKILL.md, agents/streaming-realtime-architect.md, docs/streaming/prompt-coverage.md, docs/DELIVERY-LEDGER.md, docs/EVOLUTION-CURRENT.md, docs/superpowers/STATUS.md, README.md, manifest.json]
    covers: [AC6]
    test: {path: tests/test_docs_coverage.py, name: test_manifest_counts_match_measurements}
---

# STREAMING_END_TO_END_PIPELINE — plano

Cada tarefa começa com teste vermelho específico, implementa uma mudança
primária e repete o mesmo teste verde. Goldens são gerados por CLI/core, nunca
escritos manualmente a partir de uma expectativa não executada.

## T1 — contrato e selectors

Criar `streaming_pipeline.py` com parser fail-closed para `schema_version: 1`,
nodes/edges, selectors `kind` + attrs escalares, match único, ids de facts,
provenance e unresolved nomeado. O teste cobre pipeline completo e zero/múltiplo
match.

## T2 — composição e regra

Registrar `mode=pipeline` no compositor, produzir `streaming.pipeline.node`,
`streaming.pipeline.link`, `streaming.pipeline`, `streaming.pipeline.unresolved`
e `streaming.composition.analyzed`, e adicionar `SF-STREAM-015` para blind spots.

## T3 — portas existentes

Adicionar `pipeline_path` opcional, escolha `pipeline` e encaminhamento igual em
core, CLI e MCP; manter modes anteriores byte/shape compatíveis.

## T4 — corpus

Adicionar quatro fixtures: completo, selector ausente, selector ambíguo e
contrato inválido. Runner verifica facts, findings, ids únicos e schema.

## T5 — documentação e registros

Documentar contrato e limites, sincronizar mirrors/referências, atualizar locks e
contadores medidos. Rodar gates derivados da mudança e SDD check.
