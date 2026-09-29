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

## Gate one evidence

`tests/test_decision_contract_hardening.py` cobre extras, opcionais, referências, conditions e
confidence; regressões do kernel passam no mesmo lote. Schema aberto exige
`state.additional_properties: true`; por default, extras geram `undeclared_state.*`.

## Gate two evidence

`tests/test_decision_cache_versions.py` prova mudança de policy/calibration como identidade nova,
enforcement de limite de entradas e compatibilidade da facade economy. A chave efetiva carrega
versão de schema e os componentes de identidade; um cache sem esses componentes não pode produzir
hit semântico.

## Gate four evidence

tests/test_decision_authority.py prova authority explícita, assisted com veto legado e active
com rollback. Receipts mantêm compatibilidade no bloco control e adicionam authority e
legacy_vetoed como campos semânticos. A promoção active continua exigindo activation evidence;
assisted nunca recebe autoridade de execução.

## Gate five evidence

tests/test_host_adapters.py cobre os três adapters sobre mappings gravados, com usage observado
e ausência de usage unresolved. O import graph de sparkforge/decision continua sem SDK/provider,
MCP ou chamada de rede.

## Gate three evidence

`tests/test_recovery_governance.py` prova consumo de `CaseBudget`, re-resolução por
profile/risco e encerramento de budget exaurido. `tests/test_recovery_policy.py` prova que
fingerprint repetida não retorna `replan` não-terminal. O controller gera receipt `kind: recovery`
com referência ao receipt-base.

## Gate six evidence

`tests/test_benchmark_quality_tokens_cost.py` e `tests/test_decision_replay.py` provam corpus
rotulado com cobertura de domínios, train/holdout e profiles com runners old/new.
Cada row separa qualidade, `payload_bytes`, `provider_tokens` e custo. O comparador recusa
`input_manifest` divergente e volume acima do limite configurado; tokens sem transcript e custo sem
`cost_basis` permanecem unresolved com razão explícita. O fixture é replay offline e não
autoriza claim de economia de provider.

## Gate seven evidence

`tests/test_kernel_authority.py` prova que contrato genérico `mode: active` recusa sem
`ActivePromotion`, recusa evidência incompleta e aceita somente registro que casa contrato,
versão, corpus mínimo, quality/economy gates, CI e rollback. A validação ocorre antes do
cache, impedindo bypass por decisão active cacheada. `agentic_control_plane.yaml` declara
`shadow` como default e active disabled; o bridge economy recebe promoção explicitamente sem
alterar o caminho legacy. Receipts preservam o registro de promoção.

## Completion update — 2026-09-28

O build substituiu guards locais por `sparkforge.decision.authority.AuthorityPolicy`. O motivo
`active_disabled_by_policy` vence qualquer tentativa quando a flag está desligada; ausência de
caller authority e evidência incompleta têm códigos próprios. `assisted` não é autoridade de
execução. O kernel genérico continua sem autoridade ativa por default.

O cache deixou de usar mutação global de limite: `get_key_owned()` valida owner/freshness e a
capacidade é aplicada apenas ao owner que escreve. `CacheRegistry` expõe escopos distintos para
policy, execution e evidence. Recovery e governor passam `max_retries` e `max_replans` separados,
com receipt contendo fingerprint de ciclo e snapshots antes/depois.

O protocolo de host separa `envelope_hash` da impressão canônica do transcript. Atribuição de
usage requer igualdade entre hash canônico, hash declarado e hash de usage. O benchmark de replay
adiciona `route` e valida holdout por domínio, sem score composto ou claim financeiro.
