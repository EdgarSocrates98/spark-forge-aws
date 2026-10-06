---
sdd: 1
feature: ORCHESTRATION_CONTROL_PLANE
phase: ship
profile: dev
status: done
upstream:
  path: docs/sdd/ORCHESTRATION_CONTROL_PLANE/build_report.md
  sha256: "12dc54d2aa6cb683d691086ac9b95492e6347ec063114d011be328ee58ea342e"
hypothesis_outcome: confirmed
registries: [reachability_lists, fixture_kind_coverage, snippet_measure, surface_lock, generated_reference, offline_manifest, sources_lock]
deviations:
  - "T1–T3 não registraram red/green porque a implementação precede o build_report; nenhum exit vermelho foi inventado."
  - "A validação direcionada usou basetemp dentro do workspace devido ao WinError 5 no TEMP padrão do host."
---

# ORCHESTRATION_CONTROL_PLANE — entrega

## Hipótese

Confirmada no escopo offline. O mapa normalizado preserva plataforma de origem,
controles operacionais e dependências explícitos; propriedades ausentes são
unresolved; CLI e MCP emitem o mesmo fingerprint sem disparar execução.

## O que foi entregue

- Topologia declarativa para Airflow, Dagster, Step Functions e Control-M.
- Normalização de schedules, sensors, retry/backoff, pools, concurrency,
  backfill, idempotência e dependências.
- `analyze orchestration` e `sparkforge_analyze_orchestration` com contrato
  comum.
- Fixture, parity, surface lock, referências e documentação.

## Gates rodados

- `python -m pytest tests/test_orchestration.py -q --basetemp .sparkforge/local/pytest-orchestration` — `4 passed`, exit 0.
- `python -m sparkforge_aws.adapters.cli analyze orchestration --path fixtures/orchestration/control-plane.yaml` — exit 0.
- `python -m pytest tests/test_rules_catalog_reachability.py tests/test_fixtures_kind_coverage.py -q --basetemp .sparkforge/local/pytest-orchestration-gates` — exit 0.
- `python scripts/check_surface_lock.py` — exit 0.
- `python scripts/gen_reference_docs.py --check` — exit 0.
- `python scripts/check_status_numbers.py --strict` — exit 0.
- `python scripts/verify_offline_bundle.py --repo .` — exit 0.
- `sparkforge-aws sdd check --repo . --feature ORCHESTRATION_CONTROL_PLANE` — `ok: true`.

## Limites e rollback

O analisador não aciona workflows, backfills, retries, deployments ou APIs de
orquestração. O rollback é reverter os commits da feature em ordem inversa,
mantendo os artefatos SDD.

## Lições

- Um mapa de control plane precisa manter configuração de origem junto ao
  resumo normalizado para permitir investigação sem apagar detalhes.
- `unresolved` é essencial para diferenciar propriedade ausente de propriedade
  explicitamente falsa.
