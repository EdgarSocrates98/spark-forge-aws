---
sdd: 1
feature: TOKEN_EFFICIENT_OBSERVED_ECONOMY_LIVE_GRAPH
phase: ship
profile: dev
status: done
upstream:
  path: docs/sdd/TOKEN_EFFICIENT_OBSERVED_ECONOMY_LIVE_GRAPH/build_report.md
  sha256: "47d8df9234d151f836818a66149c9df73e70b1728ce1f3740e33419d20ad346d"
hypothesis_outcome: confirmed
registries: [fixture_corpus_gates, reachability_lists, fixture_kind_coverage, snippet_measure, offline_manifest, sources_lock, generated_reference, surface_lock, status_numbers_gate, capability_parity, host_surface_contracts, token_efficient_bench, claims_gate]
deviations:
  - "A implementação já estava no checkout quando o SDD foi fechado; somente evidência verde atual foi registrada, sem fabricar RED histórico."
  - "O grafo live permanece read-only, allowlisted por manifesto e testado com clientes stubados; não há claim de acesso ou economia produtiva."
---

# TOKEN_EFFICIENT_OBSERVED_ECONOMY_LIVE_GRAPH — entrega

## Hipótese

Confirmada no escopo declarado: o Forge mede qualidade por eixo ao lado de
`payload_bytes`, resolve tokens somente de transcript e custo somente de
pricing com `cost_basis`; também compõe grafo cloud declarado sem transformar
ausência ou acesso negado em nó/aresta positiva.

## Gates

- `python scripts/check_token_efficient_bench.py` — exit 0; suite com `15` casos.
- Lote funcional de benchmark, provider economy, live graph, workspace,
  adapters e evals — `191 passed`.
- `python -m pytest tests/test_capability_parity.py tests/test_host_surface_contracts.py -q --basetemp=C:/sfpt-token-parity` — `46 passed`.
- `python -m ruff check` nos módulos, script e testes tocados — exit 0.
- `python scripts/sync_skills.py --check` — exit 0.
- `python scripts/gen_reference_docs.py --check` — exit 0.
- `python scripts/check_surface_lock.py` — exit 0.
- `python scripts/check_status_numbers.py --strict` — exit 0.
- `python scripts/verify_offline_bundle.py --check` — `69 checked`, `failed: []`.
- `sparkforge sdd check --repo . --feature TOKEN_EFFICIENT_OBSERVED_ECONOMY_LIVE_GRAPH` — `ok: true` após stamp.

## Entrega

- benchmark caso × perfil com eixos de qualidade independentes;
- parser de usage e pricing observado com recusas nomeadas;
- manifesto de recursos cloud declarados e grafo Glue/Lake Formation/S3;
- cross-account com `role_arn` explícito;
- unresolved para AccessDenied, credencial ausente, truncamento e dados
  ausentes;
- comandos `economy provider-cost` e `collect workspace-graph`.

## Rollback

Reverter os commits da capability na ordem inversa e remover juntos o
benchmark, pricing adapter, manifesto cloud, coletor e documentação de uso;
não executar mutação AWS como parte do rollback.

## Lições

Economia precisa de duas provas separadas: qualidade do contexto e medição do
provider. `payload_bytes`, `provider_tokens` e `cost_usd` não podem ser somados
nem inferidos uns dos outros.
