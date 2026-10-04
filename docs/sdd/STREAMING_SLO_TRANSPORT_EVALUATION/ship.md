---
sdd: 1
feature: STREAMING_SLO_TRANSPORT_EVALUATION
phase: ship
profile: dev
status: done
upstream:
  path: docs/sdd/STREAMING_SLO_TRANSPORT_EVALUATION/build_report.md
  sha256: "65674055c4228a0932938f11f3492aac4c0a03a8b4648afb9dd553d64d22d5ee"
hypothesis_outcome: confirmed
registries: [surface_lock, generated_reference, offline_manifest, sources_lock, status_numbers, status_numbers_gate, manifest_rule_count, reachability_lists, fixture_kind_coverage, fixture_corpus_gates, snippet_measure, rules_catalog_gates, runtime_scope_gate, sync_skills, agents_parity, sdd_check]
deviations:
  - "A extensão reutiliza mode=slo e SF-STREAM-011/012; não adiciona tool nem regra nova."
  - "kinesis.shard preserva stream_name para permitir identidade explícita sem inferir por nome de arquivo; o golden Kinesis existente foi atualizado."
  - "O script de regeneração de composição passou a extrair contract.json e aceitar --only, slo_name, transport_key e max_skew_seconds para goldens reproduzíveis."
  - "A suíte completa não foi executada; o fechamento usou gates focalizados e proporcionais ao escopo."
---

# STREAMING_SLO_TRANSPORT_EVALUATION — entrega

## Hipótese

Confirmada no escopo offline: quando um SLO Kafka ou Kinesis tem identidade,
métrica, unidade, timestamps timezone-aware e janela coberta, SparkForge
produz `met` ou `violated`; quando a evidência não basta, produz
`streaming.slo.unresolved` sem converter ausência em sucesso.

## Critérios de aceite

| critério | evidência | resultado |
|---|---|---|
| AC1–AC3 | `tests/test_facts_streaming_slo.py` | verde; identidade, Kafka/Kinesis, unidade, séries misturadas e unresolved |
| AC4 | `tests/test_analyze_streaming_composition.py::test_transport_slo_cli_and_mcp_envelopes_match` | verde; CLI/MCP/core compatíveis |
| AC5 | `fixtures/streaming_composition/slo_kafka_met`, `slo_kinesis_violated`, `slo_transport_unresolved` | verde; 3 goldens novos |
| AC6 | skill, knowledge, coverage, referências, mirrors, surface, manifest, status e SDD | verde |

## Gates rodados

| registro | comando | resultado |
|---|---|---|
| fatos/composição | pytest focalizado de SLO, ops, composition e paridade | verde; 24 testes de fatos e 18 no lote CLI/goldens |
| docs/referências/surface | pytest focalizado de coverage, references e surface | verde; 14 passed |
| mirrors | `python scripts/sync_skills.py --check` | OK |
| referências | `python scripts/gen_reference_docs.py --check` | OK |
| surface | `python scripts/check_surface_lock.py` | 0 divergências |
| bundle offline | `python scripts/verify_offline_bundle.py --check` | 69 checked, 0 failed |
| números correntes | `python scripts/check_status_numbers.py --strict` | 0 divergências |
| SDD | `sparkforge sdd check --repo . --feature STREAMING_SLO_TRANSPORT_EVALUATION` | ok |

## Entregue

- `mode=slo` para `kafka.lag` (`lag`/`records`) e `kinesis.shard`
  (`iterator_age_ms`/`ms`) com `transport_key`.
- Identidade, timestamps, janela, source facts e status preservados no fact
  derivado; unresolved nomeado para cada barreira observada.
- Paridade CLI/MCP, três fixtures novas, script de regeneração determinístico,
  knowledge, skill, mirrors, referências, surface lock, offline manifest e
  documentação corrente.

## Limites remanescentes

- Não há collector live de Kafka, Kinesis ou CloudWatch, nem SLO de sink,
  freshness, p95, disponibilidade, custo, causalidade, benchmark ou replay.
- Ausência de finding não prova SLO atendido; a série precisa ser reextraída e
  a janela declarada precisa ser coberta.
- `FORGE_LAB_DIGITAL_TWIN` e `INTEGRACAO_USUARIO` permanecem nos estados SDD
  registrados; esta feature não altera esses escopos.
