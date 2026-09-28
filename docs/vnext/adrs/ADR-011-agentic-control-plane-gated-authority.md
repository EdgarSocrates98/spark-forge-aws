# ADR-011: Agentic Decision Control Plane por gates e autoridade fail-closed

## Status

Accepted — implementação incremental iniciada em 2026-09-28.

## Context

O kernel declarativo já tinha primitivas bounded, replay local, receipts e modo shadow, mas ainda
havia lacunas de contrato, cache, recovery, rollout, adapters e benchmark. Misturar essas lacunas
em mudança única dificultaria rollback e permitiria confundir decisão aceita com autoridade de
execução.

## Decision

Implementar sete gates independentes, cada um com teste, documentação, evidência e um commit:

1. schema fechado, referências, conditions e confidence;
2. cache versionado, limite de entradas e `ArtifactCache` único;
3. `RecoveryPolicy → Governor → Budget → Receipt`, com anti-loop;
4. `shadow → assisted → active`, com veto legado;
5. adapters finos Claude/Codex/Devin, opt-in e sem SDK no core;
6. benchmark same-case de qualidade, bytes, tokens e custo;
7. promoção ativa explícita com corpus, gates, CI e rollback.

O core continua offline e provider-independent. `payload_bytes` não vira token de provider;
ausência de transcript ou `cost_basis` permanece unresolved. `SF-BENCH-001` exige caso e volume
de entrada comparáveis antes de conclusão econômica.

## Consequences

Shadow permanece default e autoridade legacy continua rollback target. Assisted pode propor, mas
legacy pode vetar. Active só é permitido após evidência explícita; benchmark sozinho nunca promove
autoridade. Cada gate pode ser revertido sem desfazer os anteriores.

## Gate 1 evidence

`tests/test_decision_contract_hardening.py` cobre extras, opcionais, referências, conditions e
confidence; regressões do kernel passam no mesmo lote. Schema aberto exige
`state.additional_properties: true`; por default, extras geram `undeclared_state.*`.

## Gate 2 evidence

`tests/test_decision_cache_versions.py` prova mudança de policy/calibration como identidade nova,
enforcement de limite de entradas e compatibilidade da facade economy. A chave efetiva aparece no
receipt como `decision|2|...`; um cache sem esses componentes não pode produzir hit semântico.
