---
sdd: 1
feature: DATA_OBSERVABILITY_SRE
phase: ship
profile: dev
status: done
upstream:
  path: docs/sdd/DATA_OBSERVABILITY_SRE/build_report.md
  sha256: "6a9accf0a2ad84429b5fb4b24f2f01b939207313127b54b113380749912253d5"
hypothesis_outcome: confirmed
registries: [reachability_lists, fixture_kind_coverage, snippet_measure, surface_lock, generated_reference, offline_manifest, sources_lock]
deviations:
  - "T1–T3 não registraram red/green porque a implementação precede o build_report; nenhum exit vermelho foi inventado."
  - "A validação direcionada usa basetemp dentro do workspace quando executada neste host, devido ao WinError 5 no TEMP padrão."
---

# DATA_OBSERVABILITY_SRE — entrega

## Hipótese

Confirmada no escopo offline. Medições numéricas compatíveis produzem status,
compliance e consumo de error budget determinísticos; ausência de medição,
unidade incompatível, incidente aberto ou timestamp inválido vira unresolved.
Dependências e blast radius são preservados sem inferir root cause.

## O que foi entregue

- Evaluator offline de freshness, completeness, latency, lag, throughput e
  availability com target, operador, unidade e janela declarados.
- Error budget, incidentes com MTTR quando calculável, dependências e blast
  radius declarado.
- `analyze data-observability` e `sparkforge_analyze_data_observability` com
  contrato comum.
- Fixture OTel-like, parity, surface lock, referências e knowledge.

## Gates rodados

- `python -m pytest tests/test_data_observability.py tests/test_fixtures_golden_observability.py -q --basetemp .sparkforge/local/pytest-observability` — exit 0.
- `python -m sparkforge.adapters.cli analyze data-observability --path fixtures/observability/sre.yaml` — exit 0.
- `python -m pytest tests/test_rules_catalog_reachability.py tests/test_fixtures_kind_coverage.py -q --basetemp .sparkforge/local/pytest-observability-gates` — exit 0.
- `python scripts/check_surface_lock.py` — exit 0.
- `python scripts/gen_reference_docs.py --check` — exit 0.
- `python scripts/check_status_numbers.py --strict` — exit 0.
- `python scripts/verify_offline_bundle.py --repo .` — exit 0.
- `sparkforge sdd check --repo . --feature DATA_OBSERVABILITY_SRE` — `ok: true`.

## Limites e rollback

Não há collector live, probing de incidentes ou root-cause analysis automático.
O rollback é reverter os commits da feature em ordem inversa, preservando os
artefatos SDD para auditoria.

## Lições

- Métrica sem unidade e janela não é evidência operacional suficiente; o
  evaluator deve mantê-la unresolved.
- Saúde de dependência e blast radius ajudam roteamento, mas não substituem
  evidência causal.
