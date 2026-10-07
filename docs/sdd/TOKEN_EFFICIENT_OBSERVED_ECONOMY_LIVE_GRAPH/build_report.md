---
sdd: 1
feature: TOKEN_EFFICIENT_OBSERVED_ECONOMY_LIVE_GRAPH
phase: build_report
profile: dev
status: done
upstream:
  path: docs/sdd/TOKEN_EFFICIENT_OBSERVED_ECONOMY_LIVE_GRAPH/plan.md
  sha256: "05a733777d440b25f805f071d2fb5d4e1a7ee690494076b99edf3f735a240a46"
tasks:
  - id: T1
    status: skipped
    green: {command: "python -m pytest tests/test_token_efficient_benchmark.py -q --basetemp=C:/sfpt-token-economy-core", exit: 0}
  - id: T2
    status: skipped
    green: {command: "python -m pytest tests/test_provider_economy.py -q --basetemp=C:/sfpt-token-economy-core", exit: 0}
  - id: T3
    status: skipped
    green: {command: "python -m pytest tests/test_collect_live_graph.py tests/test_workspace_semantic_graph.py tests/test_workspace_adapters.py tests/test_workspace_federation.py -q --basetemp=C:/sfpt-token-economy-graph", exit: 0}
  - id: T4
    status: skipped
    green: {command: "python -m pytest tests/test_adapters_cli.py tests/test_economy_report.py tests/test_evals_token_efficiency.py -q --basetemp=C:/sfpt-token-economy", exit: 0}
claims:
  - {text: "A matriz mede qualidade por eixo e mantém payload_bytes separado de provider_tokens, sem score composto.", evidence_ref: "tests/test_token_efficient_benchmark.py"}
  - {text: "Custo de provider só resolve com usage de transcript e cost_basis declarado; unidades de token permanecem separadas.", evidence_ref: "tests/test_provider_economy.py"}
  - {text: "O grafo cloud observa somente recursos declarados e preserva cross-account, AccessDenied e truncamento como unresolved.", evidence_ref: "tests/test_collect_live_graph.py"}
  - {text: "CLI, adapters e contratos de superfície expõem a capability sem adicionar descoberta ou inferência de tokens.", evidence_ref: "tests/test_adapters_cli.py; tests/test_capability_parity.py"}
change_id: null
---

# TOKEN_EFFICIENT_OBSERVED_ECONOMY_LIVE_GRAPH — relatório do build

## Resultado

Implementação presente validada em checkout atual: benchmark por perfil e eixo,
custo observado com pricing externo, manifesto cloud declarado, coletor
read-only Glue/Lake Formation/S3 e portas CLI foram exercitados com stubs e
fixtures. O lote funcional terminou com `191 passed`; o parity/surface gate
terminou com `46 passed`.

## Honestidade do RED/GREEN

O código desta feature já existia antes desta rodada de fechamento. Por isso o
relatório registra apenas os verdes realmente executados agora; nenhum RED
histórico foi inventado. A confirmação não mede economia percentual nem prova
acesso AWS produtivo.

As tarefas estão marcadas `skipped` no frontmatter por não haver RED honesto
disponível nesta rodada; elas não representam trabalho ausente. Cada uma tem o
verde reproduzido acima e o motivo fica registrado neste corpo, conforme o
contrato `sdd-build`.

## Desvios e limites

- `provider_tokens` só aparece quando transcript válido fornece usage; bytes
  nunca são convertidos em tokens.
- `cost_usd` exige pricing versionado com `cost_basis`; sem ele o resultado
  preserva tokens e retorna unresolved.
- O grafo aceita apenas `cloud_resources` declarados, exige role explícito em
  cross-account e mantém AccessDenied, ausência de credencial e paginação
  truncada como lacunas nomeadas.
- Testes live usam clientes AWS stubados; credenciais, região e permissões
  reais continuam responsabilidade do operador.
