---
sdd: 1
feature: STREAMING_SCHEMA_REGISTRY_COLLECTOR
phase: build_report
profile: dev
status: done
upstream:
  path: docs/sdd/STREAMING_SCHEMA_REGISTRY_COLLECTOR/plan.md
  sha256: 7ee9f7f86715f473947b26d2fb4f9b3351f27f4e43d96374f6d917fbe03776d0
tasks:
  - id: T1
    status: done
    red:
      command: python -m pytest tests/test_collect_schema_registry.py -q --basetemp=E:\\projetos\\spark-forge-aws\\.pytest-tmp-schema-collector-red
      exit: 2
    green:
      command: python -m pytest tests/test_collect_schema_registry.py::test_collector_paginates_and_preserves_schema_versions tests/test_collect_schema_registry.py::test_collector_cache_is_offline_and_manifested -q --basetemp=E:\\projetos\\spark-forge-aws\\.pytest-tmp-schema-collector-t1
      exit: 0
  - id: T2
    status: done
    red:
      command: python -m pytest tests/test_collect_schema_registry.py::test_cli_and_mcp_schema_registry_collection_match -q --basetemp=E:\\projetos\\spark-forge-aws\\.pytest-tmp-schema-collector-t2-red
      exit: 1
    green:
      command: python -m pytest tests/test_collect_schema_registry.py tests/test_adapters_tools.py::TestToolSurface tests/test_fixtures_golden_mcp_parity.py -q --basetemp=E:\\projetos\\spark-forge-aws\\.pytest-tmp-schema-build
      exit: 0
  - id: T3
    status: done
    red:
      command: python -m pytest tests/test_collect_schema_registry.py::test_schema_registry_collection_docs_state_read_only_limits -q --basetemp=E:\\projetos\\spark-forge-aws\\.pytest-tmp-schema-collector-t3-red
      exit: 1
    green:
      command: python -m pytest tests/test_collect_schema_registry.py::test_schema_registry_collection_docs_state_read_only_limits -q --basetemp=E:\\projetos\\spark-forge-aws\\.pytest-tmp-schema-collector-t3
      exit: 0
claims:
  - text: "O coletor preserva latest schema version e não executa operações de escrita no Glue Schema Registry."
    evidence_ref: "tests/test_collect_schema_registry.py::test_collector_paginates_and_preserves_schema_versions"
  - text: "A mesma operação read-only está disponível pela CLI e pela tool MCP com envelope compatível."
    evidence_ref: "tests/test_collect_schema_registry.py::test_cli_and_mcp_schema_registry_collection_match"
change_id: null
---

Build concluído com TDD. O artefato coletado é diretamente consumível por
`analyze schema-registry`; definições ausentes, inválidas ou acima do limite
permanecem `unresolved`. O coletor grava somente artefato e manifesto local.
