---
sdd: 1
feature: AGENTIC_ECONOMY_COMPLETION
phase: plan
profile: dev
status: ready
upstream:
  path: docs/sdd/AGENTIC_ECONOMY_COMPLETION/design.md
  sha256: "0cf5344736e8c7f10e46d71c74d7699ff94c9d1b2d22f3ce61609195a8094e96"
tasks:
  - id: T1
    files: [sparkforge/workspace/federation.py, sparkforge/workspace/__init__.py, sparkforge/workspace/manifest.py, tests/test_workspace_federation.py]
    covers: [AC1]
    test: {path: tests/test_workspace_federation.py, name: test_static_and_live_graph_compose_with_explicit_bridge}
  - id: T2
    files: [sparkforge/knowledge_engine/packs.py, tests/test_knowledge_compiler.py]
    covers: [AC2]
    test: {path: tests/test_knowledge_compiler.py, name: test_descriptors_reuse_unchanged_manifest_without_reading_pack_bodies}
  - id: T3
    files: [sparkforge/adapters/mcp_compact.py, sparkforge/adapters/mcp.py, fixtures/mcp_parity/compact_tools_list.json, fixtures/mcp_parity/compact_calls.json, tests/test_adapters_mcp_compact.py, tests/test_adapters_mcp_compact_parity.py, tests/test_adapters_mcp.py, tests/test_host_surface_contracts.py, docs/surface.lock.json]
    covers: [AC3]
    test: {path: tests/test_adapters_mcp_compact.py, name: test_compact_catalog_splits_read_and_mutation_execution}
  - id: T4
    files: [tests/test_suite_batches.py]
    covers: [AC4]
    test: {path: tests/test_suite_batches.py, name: test_a_soma_dos_lotes_e_o_tamanho_da_suite}
---

# AGENTIC_ECONOMY_COMPLETION — plano

## T1 — união static/live

Teste primeiro: criar `tests/test_workspace_federation.py` com um
`SemanticGraph`, um artifact mapping contendo account/Glue/Lake Formation/S3 e
uma bridge declarada; rodar:

```bash
python -m pytest tests/test_workspace_federation.py::test_static_and_live_graph_compose_with_explicit_bridge -q
```

O teste deve falhar por import ausente de `compose_workspace_graph`. Implementar
`GraphLink`, validação `federated_links` no manifest e o compositor usando
`semantic_graph_fragment`, `artifact_graph_fragment` e `compose_federated_graph`.
Repetir o comando e o gate de workspace. Commit: `feat: compose static and live workspace graph`.

## T2 — cache de descriptors

Adicionar teste que chama `descriptors()` uma vez, substitui `Path.read_bytes`
por uma função que falha, chama novamente e confirma hit sem leitura; depois
alterar um arquivo e confirmar novo `source_hash`. Rodar:

```bash
python -m pytest tests/test_knowledge_compiler.py::test_descriptors_reuse_unchanged_manifest_without_reading_pack_bodies -q
```

O teste deve falhar porque o registry relê corpos. Implementar assinatura
ordenada de caminhos/tamanho/mtime e cache no `PackRegistry`; recalcular digest
somente em miss. Rodar o mesmo teste e os testes de knowledge. Commit:
`perf: cache knowledge pack descriptor scans`.

## T3 — split execute read/mutation

Atualizar testes/goldens para sete operações, adicionar teste de annotations e
recusas cruzadas, e rodar:

```bash
python -m pytest tests/test_adapters_mcp_compact.py::test_compact_catalog_splits_read_and_mutation_execution -q
```

O teste deve falhar porque só existe `execute`. Implementar os dois schemas e
handlers sobre o dispatcher existente, atualizar parity/golden/surface lock e
rodar `python scripts/check_surface_lock.py`. Commit:
`feat: split compact MCP read and mutation execution`.

## T4 — suíte monolítica

Rodar a suíte inteira com TEMP/cache externo se necessário:

```bash
python -m pytest -q
```

O resultado esperado é exit 0; registrar contagem, skips e warnings no
build report. Em seguida rodar `python scripts/check_surface_lock.py`,
`python scripts/check_token_efficient_bench.py`, `ruff check sparkforge scripts tests`
e `git diff --check`. Commit: `test: complete monolithic suite validation`.
