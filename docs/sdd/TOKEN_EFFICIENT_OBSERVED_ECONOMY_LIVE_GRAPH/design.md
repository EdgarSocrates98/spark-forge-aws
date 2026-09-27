---
sdd: 1
feature: TOKEN_EFFICIENT_OBSERVED_ECONOMY_LIVE_GRAPH
phase: design
profile: dev
status: ready
upstream:
  path: docs/sdd/TOKEN_EFFICIENT_OBSERVED_ECONOMY_LIVE_GRAPH/define.md
  sha256: "4a1c4d630f91baca7b569e3a0e6021fbc3a2ccf851b64bc1a868812356e6e9a0"
files:
  - {path: evals/token_efficient/suite.yaml, action: modify, reason: "suite ampla, eixos de qualidade e casos de perfis"}
  - {path: evals/token_efficient/fixtures/quality_cases.yaml, action: modify, reason: "gabarito deterministico dos mesmos casos"}
  - {path: scripts/run_token_efficient_bench.py, action: create, reason: "runner reproduzivel da matriz local"}
  - {path: sparkforge/evals/token_benchmark.py, action: create, reason: "loader, matriz e comparacao por eixo sem score composto"}
  - {path: sparkforge/evals/runner.py, action: modify, reason: "usar default de profile quando max_bytes nao e declarado e transportar suite_id"}
  - {path: sparkforge/economy/provider_cost.py, action: create, reason: "calculo observado de custo com pricing externo e cost_basis obrigatorio"}
  - {path: sparkforge/adapters/_core.py, action: modify, reason: "compor provider-cost e collect workspace-graph nos verbos de topo"}
  - {path: sparkforge/adapters/cli.py, action: modify, reason: "expor benchmark, provider-cost e workspace-graph"}
  - {path: sparkforge/workspace/manifest.py, action: modify, reason: "validar cloud_resources declarados e seus limites"}
  - {path: sparkforge/collect/live_graph.py, action: create, reason: "coletor read-only de Glue, Lake Formation e S3 com cross-account explicito"}
  - {path: sparkforge/collect/__init__.py, action: modify, reason: "exportar coletor live"}
  - {path: tests/test_token_efficient_benchmark.py, action: create, reason: "AC1, AC2 e AC3"}
  - {path: tests/test_provider_economy.py, action: create, reason: "AC4 e recusas de pricing/transcript"}
  - {path: tests/test_workspace_semantic_graph.py, action: modify, reason: "AC5 para cloud_resources"}
  - {path: tests/test_collect_live_graph.py, action: create, reason: "AC6, AC7 e AC8 com boto3 stubado"}
  - {path: tests/test_adapters_cli.py, action: modify, reason: "AC9 dos tres comandos"}
  - {path: docs/guia/usos/economia-de-contexto.md, action: modify, reason: "uso do benchmark, transcript e pricing declarado"}
decisions:
  - id: D1
    choice: "Matriz conserva quality_axes, payload_bytes e provider_tokens como medidas independentes; compare publica transicoes por eixo e nunca score composto."
    rejected: ["normalizar qualidade por tokens, que escolheria pesos sem medida", "somar bytes e tokens, unidades diferentes"]
    rollback: "git revert do commit da matriz e dos modulos sparkforge/evals/token_benchmark.py e scripts/run_token_efficient_bench.py"
  - id: D2
    choice: "Pricing entra por JSON fornecido pelo operador com cost_basis e moeda; tokens continuam vindo exclusivamente de transcript valido."
    rejected: ["preco embutido por provider/modelo, que envelhece e inventa fonte", "estimar tokens por bytes, proibido pelas regras 22 e 24"]
    rollback: "git revert do commit de sparkforge/economy/provider_cost.py e das flags economy provider-cost"
  - id: D3
    choice: "Grafo live aceita somente cloud_resources de workspace.yaml e grava estados de cada chamada; nao faz descoberta global."
    rejected: ["listar toda a conta AWS, que amplia dados e permissao sem pergunta declarada", "tratar EntityNotFound ou AccessDenied como ausencia"]
    rollback: "git revert do commit de sparkforge/collect/live_graph.py, manifest.py e do subcomando workspace-graph"
  - id: D4
    choice: "Cross-account exige account_id divergente observada mais role_arn explicito; assume-role e somente read-only para a coleta declarada."
    rejected: ["inferir role pelo nome do recurso", "usar a credencial local contra conta diferente e chamar isso de cross-account"]
    rollback: "git revert do mesmo commit e remover cloud_resources do manifesto; a coleta local existente permanece"
covers:
  - {part: "benchmark e comparacao", acceptance: [AC1, AC2, AC3]}
  - {part: "provider usage e custo", acceptance: [AC4]}
  - {part: "manifesto cloud", acceptance: [AC5]}
  - {part: "coleta live e cross-account", acceptance: [AC6, AC7, AC8]}
  - {part: "superficie CLI e guia", acceptance: [AC9]}
---

# TOKEN_EFFICIENT_OBSERVED_ECONOMY_LIVE_GRAPH — desenho

## Arquitetura

```text
suite.yaml + quality_cases.yaml
        │
        ▼
token_benchmark ──► EvaluationRunner ──► matriz caso × perfil
        │                                      │
        └──────── compare por eixo ◄───────────┘

host transcript ──► read_host_usage ──► provider_cost ◄── pricing.json
                                           │
                                           └── cost_usd somente com cost_basis

workspace.yaml ──► WorkspaceManifest.cloud_resources
        │
        ▼
collect workspace-graph ──► boto3 STS/Glue/Lake Formation/S3
        │                     │
        │                     ├── nodes/edges declarados
        │                     └── unresolved por chamada/conta/paginacao
        ▼
.sparkforge/artifacts/workspace_graph/<workspace>.json
```

## Partes

| parte | arquivos | critério |
|---|---|---|
| benchmark amplo | `evals/token_efficient/*`, `sparkforge/evals/token_benchmark.py`, `sparkforge/evals/runner.py`, `scripts/run_token_efficient_bench.py` | AC1-AC3 |
| custo observado | `sparkforge/economy/provider_cost.py`, `sparkforge/adapters/_core.py`, `sparkforge/adapters/cli.py` | AC4, AC9 |
| manifesto cloud | `sparkforge/workspace/manifest.py` | AC5 |
| coletor live | `sparkforge/collect/live_graph.py`, `sparkforge/collect/__init__.py` | AC6-AC8 |
| testes e guia | `tests/test_token_efficient_benchmark.py`, `tests/test_provider_economy.py`, `tests/test_workspace_semantic_graph.py`, `tests/test_collect_live_graph.py`, `tests/test_adapters_cli.py`, `docs/guia/usos/economia-de-contexto.md` | AC1-AC9 |

## Contratos

### Benchmark

`run_token_efficient_bench.py` carrega somente a suite versionada e materializa
cada caso nos tres perfis. O JSON de saida tem `results` por caso/perfil e
`summary` com valores crus: `payload_bytes`, `evidence_recall`,
`false_positive_rate`, status, unresolved e plano. `provider_tokens` permanece
`null` quando a execucao nao recebe transcript; o runner nao inventa usage.

### Provider cost

Pricing JSON exige `schema_version`, `currency`, `cost_basis`, `source` e
`rates` para `input_tokens`, `output_tokens`, `cache_read_tokens` e
`cache_creation_tokens`. A funcao calcula cada componente separadamente e
retorna `cost_usd`/`cost_total` somente se todos os tokens e taxas necessarios
estiverem resolvidos. Qualquer lacuna preserva os tokens medidos e adiciona
`unresolved`, sem substituir valor por zero.

### Grafo live

`cloud_resources` e uma allowlist validada: id unico, kind `dataset`,
`services` entre `glue`, `lakeformation`, `s3`, e campos de identidade. Cada
recurso gera um node de conta e um node de recurso. Glue mede tabela e
`StorageDescriptor.Location`; Lake Formation mede grants/settings; S3 mede
objetos apenas sob bucket/prefix declarados, com teto e `truncated` explicito.
Erro de API preserva `service`, `error_code`, `status` e `resource_id` em
`unresolved`. Nenhuma chamada e feita para conta divergente sem role_arn.

## Conhecimento consultado

- `sparkforge.collect.host_usage` e `sparkforge.facts.host_transcript`, lidos
  por import/testes e usados como contrato local de usage do host.
- `sparkforge.collect.lakeformation`, `sparkforge.collect.glue_resource_link`
  e `sparkforge.collect.iam_access`, lidos por `sparkforge code search`/fonte,
  como precedentes de status por chamada, catalog_id explicito e simulacao.
- `docs/guia/usos/economia-de-contexto.md`, como contrato publicado de bytes,
  tokens unresolved e cost_basis.

## Rollback operacional

Reverter o commit da feature remove os tres novos comandos e o coletor live;
artefatos ja gravados permanecem no workspace para auditoria e podem ser
removidos manualmente pelo operador depois de verificar o recibo. Nenhum
comando desta feature aplica mudanca na AWS.
