---
sdd: 1
feature: STREAMING_SLO_EVALUATION
phase: ship
profile: dev
status: done
upstream:
  path: docs/sdd/STREAMING_SLO_EVALUATION/build_report.md
  sha256: "8d8c3a350fff9050e4d586e5b7c955bcaf7a13363322c925f0ad620b24acd80f"
hypothesis_outcome: confirmed
registries: [surface_lock, generated_reference, offline_manifest, sources_lock, status_numbers, status_numbers_gate, manifest_rule_count, reachability_lists, fixture_kind_coverage, fixture_corpus_gates, snippet_measure, rules_catalog_gates, runtime_scope_gate, sync_skills, agents_parity, sdd_check]
deviations:
  - "Os novos ids foram SF-STREAM-011 e SF-STREAM-012 porque SF-STREAM-010 já era o id de OpenLineage no catálogo."
  - "manifest.json foi atualizado de 210 para 212 regras depois do gate documental medir o catálogo real."
  - "knowledge/offline-manifest.json recebeu o checksum do knowledge/streaming-operations.md após a documentação SLO."
  - "A suíte completa não foi executada; o fechamento usou somente gates focalizados e proporcionais."
---

# STREAMING_SLO_EVALUATION — entrega

## Hipótese

Confirmada no escopo offline: quando contrato SLO, query, métrica, unidade,
operador, timestamps e janela são declarados e observados em batches de
Structured Streaming, SparkForge distingue `met` de `violated`; quando a
evidência não basta, publica `streaming.slo.unresolved`.

## Critérios de aceite

| critério | evidência | resultado |
|---|---|---|
| AC1–AC3 | `tests/test_facts_streaming_slo.py` | verde; 10 passed |
| AC4 | `tests/test_streaming_rules.py::test_slo_evaluation_rules_are_evidence_first` | verde |
| AC5 | `tests/test_analyze_streaming_composition.py::test_slo_cli_and_mcp_envelopes_match` | verde |
| AC6 | `fixtures/streaming_composition/slo_*` e `tests/test_fixtures_golden_streaming_composition.py` | verde; 2 goldens |
| AC7 | skill, knowledge, coverage, referências, mirrors, surface, manifests, números e SDD | verde |

## Gates rodados

| registro | comando | resultado |
|---|---|---|
| foco de facts/regras/portas/goldens | pytest focalizado de SLO, streaming composition, rules e fixtures | verde; 16 testes combinados e 2 goldens |
| docs, referências e surface | `python -m pytest tests/test_docs_coverage.py tests/test_reference_docs.py tests/test_surface_lock.py -q` | 40 passed |
| catálogo e reachability | `python -m pytest tests/test_fixtures_kind_coverage.py tests/test_rules_catalog_reachability.py -q` | 919 passed |
| snippet measure | `python -m pytest tests/test_harness_untrusted.py -q` | 4 passed |
| mirrors | `python scripts/sync_skills.py --check` | OK |
| referências | `python scripts/gen_reference_docs.py --check` | OK |
| surface | `python scripts/check_surface_lock.py` | 0 divergências |
| bundle offline | `python scripts/verify_offline_bundle.py --check --repo .` | 69 checked, 0 failed |
| números correntes | `python scripts/check_status_numbers.py --strict` | 0 divergências |
| SDD | `sparkforge-aws sdd check --repo . --feature STREAMING_SLO_EVALUATION` | ok |

## Entregue

- `sparkforge_aws/facts/streaming_slo.py` com avaliação direta de progress e
  unresolved nomeado.
- `mode=slo`, `slo_name`, portas CLI/MCP e envelope compartilhado.
- `SF-STREAM-011` para violação observada e `SF-STREAM-012` para evidência
  incompleta, ambos evidence-first.
- Fixtures `slo_met`, `slo_violated` e `slo_unresolved`, com goldens e registro
  nas coberturas manuais.
- Skill, mirrors, knowledge, prompt coverage, referências, surface lock,
  manifests, README, guias, STATUS, evolução, ledger e SDD até ship.

## Limites remanescentes

- Não há collector live de CloudWatch, Kafka, Kinesis, Spark ou Glue.
- Não há p95/freshness/availability, conversão de unidade, SLO de transport ou
  sink, custo, causalidade, benchmark ou replay funcional.
- Ausência de finding não prova SLO atendido; a série precisa ser reextraída e
  a janela declarada precisa ser coberta.
- `FORGE_LAB_DIGITAL_TWIN` e `INTEGRACAO_USUARIO` permanecem nos estados SDD
  registrados; esta feature não altera esses escopos.
