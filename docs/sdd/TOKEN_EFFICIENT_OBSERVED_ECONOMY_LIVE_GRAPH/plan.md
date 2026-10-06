---
sdd: 1
feature: TOKEN_EFFICIENT_OBSERVED_ECONOMY_LIVE_GRAPH
phase: plan
profile: dev
status: ready
upstream:
  path: docs/sdd/TOKEN_EFFICIENT_OBSERVED_ECONOMY_LIVE_GRAPH/design.md
  sha256: "2233c78a80f89eca500a955f14c7d9ee47a3e53348da0d7f2cecaff41a176edb"
tasks:
  - id: T1
    files: [evals/token_efficient/suite.yaml, evals/token_efficient/fixtures/quality_cases.yaml, sparkforge_aws/evals/runner.py, sparkforge_aws/evals/token_benchmark.py, scripts/run_token_efficient_bench.py, tests/test_token_efficient_benchmark.py]
    covers: [AC1, AC2, AC3]
    test: {path: tests/test_token_efficient_benchmark.py, name: test_suite_ampla_tem_eixos_e_casos_unicos}
  - id: T2
    files: [sparkforge_aws/economy/provider_cost.py, sparkforge_aws/adapters/_core.py, sparkforge_aws/adapters/cli.py, tests/test_provider_economy.py]
    covers: [AC4]
    test: {path: tests/test_provider_economy.py, name: test_provider_cost_requires_cost_basis_and_keeps_token_units}
  - id: T3
    files: [sparkforge_aws/workspace/manifest.py, sparkforge_aws/collect/live_graph.py, sparkforge_aws/collect/__init__.py, tests/test_workspace_semantic_graph.py, tests/test_collect_live_graph.py]
    covers: [AC5, AC6, AC7, AC8]
    test: {path: tests/test_collect_live_graph.py, name: test_collect_live_graph_compose_glue_lakeformation_s3}
  - id: T4
    files: [sparkforge_aws/adapters/cli.py, sparkforge_aws/adapters/_core.py, docs/guia/usos/economia-de-contexto.md, tests/test_adapters_cli.py]
    covers: [AC9]
    test: {path: tests/test_adapters_cli.py, name: test_cli_exposes_observed_economy_and_live_graph_commands}
---

# TOKEN_EFFICIENT_OBSERVED_ECONOMY_LIVE_GRAPH — plano

## T1 — benchmark amplo por eixo

Adicionar casos a `suite.yaml` e ao gabarito, mantendo os mesmos ids nos dois
arquivos. Os casos devem cobrir resposta normal, recusa por budget, evidencia
critica, conflito, unresolved, findings esperados, knowledge/code e os tres
perfis. Em `EvaluationRunner`, `max_bytes` ausente passa como `None` para que o
Gateway use o default do profile. `token_benchmark.py` deve carregar a suite,
rodar matriz caso × profile e comparar duas matrizes por `payload_bytes`,
`evidence_recall`, `false_positive_rate`, status, unresolved e plano, sem
criar campo score/delta composto. O script aceita somente a suite versionada e
escreve JSON em `--out`.

Teste primeiro em `tests/test_token_efficient_benchmark.py`:

```python
def test_suite_ampla_tem_eixos_e_casos_unicos():
    suite = load_benchmark_suite(ROOT / "evals" / "token_efficient")
    assert len(suite["cases"]) >= 12
    assert len({case["id"] for case in suite["cases"]}) == len(suite["cases"])
    assert set(suite["quality_axes"]) >= {
        "status", "evidence_recall", "false_positive_rate", "unresolved", "execution_plan"
    }
```

Rodar antes do código:

```bash
python -m pytest tests/test_token_efficient_benchmark.py::test_suite_ampla_tem_eixos_e_casos_unicos -q
```

Código mínimo: implementar `load_benchmark_suite`, `run_benchmark_matrix` e
`compare_benchmark_matrix` em `sparkforge_aws/evals/token_benchmark.py`, usar
`EvaluationRunner.run_context_benchmark` e retornar somente medidas separadas.
Adicionar `scripts/run_token_efficient_bench.py` como wrapper da função. Rodar
depois os três testes AC1-AC3 e `python scripts/check_token_efficient_bench.py`.
Commit: `feat: expand token-efficient quality benchmark`.

## T2 — usage do provider e custo observado

Criar `sparkforge_aws/economy/provider_cost.py` com schema fechado para pricing:
`schema_version`, `currency`, `cost_basis`, `source` e taxas por unidade. Ler
transcript via `read_host_usage`, manter cada unidade de token separada e
recusar custo se usage, taxa ou `cost_basis` faltar. Ligar o comando
`sparkforge-aws economy provider-cost --host-transcript <jsonl> --pricing <json>` ao
core/CLI; não alterar o cálculo de payload bytes.

Teste primeiro:

```python
def test_provider_cost_requires_cost_basis_and_keeps_token_units(tmp_path):
    transcript = write_transcript_with_usage(tmp_path)
    pricing = write_pricing(tmp_path, cost_basis="operator:test", source="fixture")
    result = provider_cost(transcript, pricing)
    assert result["tokens"] == {
        "input_tokens": 100,
        "output_tokens": 20,
        "cache_read_tokens": 30,
        "cache_creation_tokens": 4,
    }
    assert result["cost_basis"] == "operator:test"
    assert result["cost_usd"] > 0
```

Rodar o teste antes do módulo, ver `ModuleNotFoundError` da unidade sob teste;
implementar o módulo, as recusas nomeadas e o adapter; rodar AC4 e
`tests/test_economy_report.py -q`. Commit: `feat: report observed provider cost`.

## T3 — manifesto e grafo AWS live

Adicionar `cloud_resources` ao `WorkspaceManifest`, validando ids unicos,
services permitidos, nomes e campos sem `..` ou descoberta implícita. Criar
`sparkforge_aws/collect/live_graph.py` sem importar boto3 no topo. O coletor deve
observar a conta via STS, exigir `role_arn` quando `account_id` divergir,
assumir role somente nesse caso, chamar apenas Glue/Lake Formation/S3
declarados, limitar paginas/objetos, e escrever status/unresolved verbatim.

Testes primeiro em `tests/test_collect_live_graph.py`:

```python
def test_collect_live_graph_compose_glue_lakeformation_s3(monkeypatch, tmp_path):
    monkeypatch.setattr(live_graph, "require_boto3", lambda: fake_aws())
    manifest = write_manifest(tmp_path, account_id="111111111111")
    result = collect_workspace_graph(manifest, tmp_path, now="2026-09-27T00:00:00Z")
    assert {node["kind"] for node in result["graph"]["nodes"]} >= {
        "account", "glue_table", "lakeformation", "s3_prefix"
    }
    assert {edge["relation"] for edge in result["graph"]["edges"]} >= {
        "catalog_contains", "governed_by", "stored_at"
    }
```

Adicionar também os testes de role obrigatório e de estados unresolved. Rodar
antes, implementar o mínimo no manifesto/coletor, rodar os três testes e
`tests/test_workspace_semantic_graph.py -q`. Commit: `feat: collect declared live data graph`.

## T4 — CLI, guia e gates

Adicionar os parsers/dispatchers dos comandos, testar a ajuda/roteamento pelo
adapter existente e documentar transcript, pricing e manifesto live em
`docs/guia/usos/economia-de-contexto.md`. Rodar:

```bash
python -m pytest tests/test_adapters_cli.py::test_cli_exposes_observed_economy_and_live_graph_commands -q
ruff check sparkforge_aws scripts tests
python scripts/check_surface_lock.py
python scripts/check_token_efficient_bench.py
git diff --check
```

Commit: `feat: expose observed economy and live graph commands`.
