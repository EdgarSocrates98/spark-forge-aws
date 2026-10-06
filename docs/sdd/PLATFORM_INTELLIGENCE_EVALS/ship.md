---
sdd: 1
feature: PLATFORM_INTELLIGENCE_EVALS
phase: ship
profile: dev
status: done
upstream:
  path: docs/sdd/PLATFORM_INTELLIGENCE_EVALS/build_report.md
  sha256: "f9293922404e8653b267bdaafe966edbb9fbc1b566c752ef533e28526a639e5e"
hypothesis_outcome: confirmed
registries: [offline_manifest, sources_lock]
deviations:
  - "T1–T2 não registraram red/green porque a implementação precede o build_report; nenhum exit vermelho foi inventado."
  - "A validação direcionada usou basetemp dentro do workspace devido ao WinError 5 no TEMP padrão do host."
---

# PLATFORM_INTELLIGENCE_EVALS — entrega

## Hipótese

Confirmada para o contrato seed offline. Cada caso preserva expected facts,
findings, proibições, unresolved, evidence, routing, arquitetura e limites de
economia; bytes e chamadas são medidos separadamente de provider tokens, que
permanecem unresolved sem transcript do host.

## O que foi entregue

- `evals/platform_intelligence/suite.yaml` com oito casos cobrindo graph,
  Forge Lab, catalog, dbt, DuckDB, observability, orchestration e ecosystem.
- `scripts/check_platform_eval_contract.py` com validação de shape e política
  de tokens.
- Testes de contrato e documentação de expansão para corpus real e holdout.

## Gates rodados

- `python scripts/check_platform_eval_contract.py --path evals/platform_intelligence/suite.yaml` — exit 0, 8/8 casos válidos.
- `python -m pytest tests/test_platform_evals.py -q --basetemp .sparkforge/local/pytest-platform-evals` — `2 passed`, exit 0.
- `python scripts/verify_offline_bundle.py --repo .` — exit 0.
- `python scripts/check_status_numbers.py --strict` — exit 0.
- `sparkforge-aws sdd check --repo . --feature PLATFORM_INTELLIGENCE_EVALS` — `ok: true`.

## Limites e rollback

O seed não mede recall/precision de produção, savings, provider tokens ou custo
financeiro. O rollback é reverter `0721e1c` e `d7e8c8c`, mantendo a política de
unresolved e o histórico SDD.

## Lições

- Evals precisam carregar proibições e blind spots, não apenas resposta esperada.
- A política de economia deve recusar conversão de bytes em tokens sem transcript
  observável do host.
