---
sdd: 1
feature: STREAMING_MANAGED_FLINK_COLLECTOR
phase: plan
profile: dev
status: ready
upstream:
  path: docs/sdd/STREAMING_MANAGED_FLINK_COLLECTOR/design.md
  sha256: "1d7c509019d63beef8709d8dcf920142e99f82e4987037576b2e0b9124180952"
tasks:
  - id: T1
    files: [tests/test_collect_managed_flink.py, sparkforge/collect/managed_flink.py, sparkforge/collect/base.py]
    covers: [AC1, AC2]
    test: {path: tests/test_collect_managed_flink.py, name: test_collector_normalizes_describe_response}
  - id: T2
    files: [sparkforge/adapters/_core.py, sparkforge/adapters/cli.py, sparkforge/adapters/tools.py, parity.yaml, manifest.json, tests/test_collect_managed_flink.py]
    covers: [AC3]
    test: {path: tests/test_collect_managed_flink.py, name: test_cli_and_mcp_managed_flink_collection_match}
  - id: T3
    files: [tests/test_collect_managed_flink.py, sparkforge/adapters/_core.py]
    covers: [AC4]
    test: {path: tests/test_collect_managed_flink.py, name: test_collected_artifact_feeds_managed_flink_analyzer}
  - id: T4
    files: [knowledge/flink-streaming.md, docs/streaming/prompt-coverage.md, docs/guia/03-cli.md, docs/guia/04-mcp.md]
    covers: [AC1, AC2, AC3, AC4]
    test: {path: tests/test_collect_managed_flink.py, name: test_managed_flink_collection_docs_state_read_only_limits}
---

# STREAMING_MANAGED_FLINK_COLLECTOR — plano

Implementação serializada em TDD. Cada tarefa começa com teste vermelho, aplica
somente o código mínimo, roda o mesmo teste verde e faz commit separado. A
integração atualiza os registros de surface junto da tool; a documentação
explicita o que `DescribeApplication` não mede.

## T1 — collector read-only e manifesto

Escrever cliente falso com `describe_application`, redaction de campos
secret-like, normalização de `ApplicationDetail`, configuração de checkpoint/
parallelism/VPC/logging, limites e cache. Rodar:

```text
python -m pytest tests/test_collect_managed_flink.py::test_collector_normalizes_describe_response tests/test_collect_managed_flink.py::test_collector_cache_is_offline_and_manifested -q
```

Esperar vermelho antes de `sparkforge/collect/managed_flink.py`; implementar
kind, path determinístico, `IncludeAdditionalDetails=False`, `_offline_hit` e
`_write_and_register`; repetir comando verde. Commit: `feat(flink): add managed flink read-only collector`.

## T2 — CLI/MCP/paridade

Adicionar parser, handler, adapter, schema MCP, handler MCP, allowlists,
parity e manifest. O teste chama CLI e MCP com clientes falsos e compara o
envelope sem paths locais. Rodar o node AC3 antes e depois. Commit:
`feat(flink): expose managed flink collector adapters`.

## T3 — analyzer offline

Analisar o artifact produzido com `artifact=managed_flink`, confirmar facts no
namespace gerenciado e ausência de `flink.*`. Rodar o node AC4 antes e depois.
Commit: `test(flink): prove managed artifact analyzer handoff`.

## T4 — conhecimento e cobertura

Documentar API, segurança, cache, ausência de métricas/job plan e o próximo
artifact necessário. Atualizar matriz de cobertura e guias; gerar referências,
surface lock e números. Rodar o teste documental e os gates da entrega. Commit:
`docs(flink): record managed collector limits`.
