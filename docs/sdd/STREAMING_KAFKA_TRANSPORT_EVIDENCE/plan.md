---
sdd: 1
feature: STREAMING_KAFKA_TRANSPORT_EVIDENCE
phase: plan
profile: dev
status: ready
upstream:
  path: docs/sdd/STREAMING_KAFKA_TRANSPORT_EVIDENCE/design.md
  sha256: "b3366dffd7b6b90efaef89c0bf5a51a762adbc897128f06e80ef411caecedac8"
tasks:
  - id: T1
    files: [tests/test_facts_transport.py, sparkforge_aws/facts/transport.py]
    covers: [AC1, AC2, AC3]
    test: {path: tests/test_facts_transport.py, name: test_kafka_explicit_lag_observations_emit_series_and_reject_insufficient}
  - id: T2
    files: [rules/catalog/streaming_observability.yaml, tests/test_streaming_rules.py]
    covers: [AC4]
    test: {path: tests/test_streaming_rules.py, name: test_kafka_transport_rules_require_observed_conditions}
  - id: T3
    files: [fixtures/transport/kafka_isr_deficit, fixtures/transport/kafka_lag_series, tests/test_fixtures_golden_transport.py]
    covers: [AC5]
    test: {path: tests/test_fixtures_golden_transport.py, name: test_transport_fixture_corpus_is_complete}
  - id: T4
    files: [knowledge/transport-diagnostics.md, skills/review-streaming-operations/SKILL.md, agents/streaming-realtime-architect.md, docs/streaming/prompt-coverage.md, tests/test_docs_coverage.py]
    covers: [AC6]
    test: {path: tests/test_docs_coverage.py, name: test_streaming_coverage_mentions_slo_evaluation}
  - id: T5
    files: [docs/DELIVERY-LEDGER.md, docs/EVOLUTION-CURRENT.md, docs/superpowers/STATUS.md, knowledge/offline-manifest.json, knowledge/sources.lock.json, docs/surface.lock.json]
    covers: [AC6]
    test: {path: tests/test_status_numbers_gate.py, name: test_o_repositorio_de_verdade_passa}
---

# STREAMING_KAFKA_TRANSPORT_EVIDENCE — plano

Executar T1 em red/green antes do extrator; T2 em red/green antes do catálogo
final; T3 gerar facts/findings determinísticos; T4 sincronizar skill, agent,
mirrors e referências; T5 atualizar registros e rodar gates. A suite completa
fica fora desta frente; apenas lotes focados e registros derivados serão
executados.

## T1 — extrator

Adicionar teste com série crescente, série insuficiente e timestamp inválido.
Implementar parser fail-closed, composição por identidade e compatibilidade do
snapshot legado. Rodar o mesmo node em red e green.

## T2 — rules

Adicionar `SF-STREAMOBS-003` e `SF-STREAMOBS-004` com `runtime_scope`, action,
fonte e `knowledge_refs`. Testar positivo, igualdade, série não monotônica,
delta não positivo e ausência de fatos.

## T3 — corpus

Criar goldens para ISR deficit e `lag_observations`; incluir cenário
não-monotônico/insuficiente. Regenerar expected facts e findings por ferramenta
determinística e validar todos os fatos pelo schema.

## T4 — conhecimento e especialistas

Documentar entrada, saída, uso econômico, limits e rollback. Atualizar
`review-streaming-operations` e `streaming-realtime-architect`; sincronizar
mirrors e referências sem criar tool/verb novo.

## T5 — fechamento

Atualizar hashes, superfície de knowledge, números correntes, ledger, evolução
e coverage. Rodar `sdd check`, `sync_skills`, referências, surface, status,
offline bundle, sources lock, catálogo, reachability e fixtures.
