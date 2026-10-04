---
sdd: 1
feature: STREAMING_SLO_LATENCY_FRESHNESS
phase: ship
profile: dev
status: done
upstream:
  path: docs/sdd/STREAMING_SLO_LATENCY_FRESHNESS/build_report.md
  sha256: "98ddc3132d0a9042405de9d60e616c662f14e9ccfae2279188cf6cb18a024cd4"
hypothesis_outcome: confirmed
registries:
  - reachability_lists
  - snippet_measure
  - agents_parity
  - fixture_corpus_gates
  - fixture_kind_coverage
  - generated_reference
  - sync_skills
  - surface_lock
  - status_numbers_gate
  - offline_manifest
  - sources_lock
deviations:
  - "A frente reutiliza streaming.slo.evaluation e não cria tool, namespace ou regra nova."
  - "O novo golden revelou drift anterior de facts temporais em goldens de composição; eles foram regenerados e mantêm o mesmo contrato de findings quando aplicável."
  - "Freshness offline não prova end-to-end latency, causa, custo, disponibilidade ou estado live."
  - "A suíte completa não foi executada nesta frente."
---

# STREAMING_SLO_LATENCY_FRESHNESS — ship

## Resultado

Ship concluído. `mode=slo` agora compara SLOs `statistic=p95` com percentil
nearest-rank e reconhece `freshness_ms` derivada de `timestamp` +
`eventTime.max` ou medida `freshnessMs` explícita. Latência end-to-end só é
aceita quando o artefato fornece `endToEndLatencyMs`.

## Aceitação

- **AC1–AC2:** statistic seguro e freshness temporal com unresolved nomeado
  estão cobertos nos extractors.
- **AC3–AC4:** p95 e latência end-to-end explícita/ausente preservam comparador,
  evidência e limites semânticos.
- **AC5:** fixture `slo_p95_freshness` e goldens de composição passam facts,
  findings, schema e determinismo.
- **AC6:** knowledge, skills canônicas, mirrors, referência gerada, prompt
  coverage e SDD descrevem a entrega e os blind spots.

## Gates executados

- 74 testes focados de facts, SLO, composição, goldens e docs passaram.
- `gen_reference_docs`, `sync_skills` e `git diff --check` foram executados;
  surface lock e manifest não exigiram alteração de superfície.
- `sparkforge sdd check --repo . --feature STREAMING_SLO_LATENCY_FRESHNESS`
  passou sem recusas ou unresolved.

## Limites e próximos desbloqueios

Collectors live, séries de longa duração, correlação observability endpoint,
latência end-to-end quando não há campo explícito, replay, benchmark,
validação funcional e atribuição causal continuam fora. O p95 é resumo de uma
amostra observada, não garantia de SLO de produção sem retenção e workload
compatíveis.
