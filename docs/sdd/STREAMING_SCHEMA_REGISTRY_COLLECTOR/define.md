---
sdd: 1
feature: STREAMING_SCHEMA_REGISTRY_COLLECTOR
phase: define
profile: dev
status: ready
upstream:
  path: docs/sdd/STREAMING_SCHEMA_REGISTRY_COLLECTOR/explore.md
  sha256: "f2a28b13c00d052263db5ad9aea0293a23413d0705973ba19589c76bf3be87e6"
hypothesis:
  claim: "Um collector Glue Schema Registry read-only produz dump reproduzível que o analyzer de contratos consegue julgar sem chamadas AWS no core."
  prediction: "Com registry/schema declarados, o collector preserva identidade, formato, compatibilidade, versão mais recente e definição quando observados; paginação, ausência de definição e falhas de escopo ficam nomeadas como unresolved."
  experiment: "Executar collector com clientes falsos paginados, analisar o dump gerado e confirmar cache local sem nova chamada AWS."
acceptance:
  - id: AC1
    statement: "O collector chama somente list/get do Glue Schema Registry, pagina resultados, limita cardinalidade e preserva unresolved para ausência/definição omitida."
    verified_by: {kind: test, ref: "tests/test_collect_schema_registry.py::test_collector_paginates_and_preserves_schema_versions"}
  - id: AC2
    statement: "O artifact registrado possui kind/schema_registry, manifesto, comando de coleta, redaction e cache que não chama AWS novamente."
    verified_by: {kind: test, ref: "tests/test_collect_schema_registry.py::test_collector_cache_is_offline_and_manifested"}
  - id: AC3
    statement: "CLI e MCP expõem a mesma operação read-only, com parâmetros declarados e envelope consistente."
    verified_by: {kind: test, ref: "tests/test_collect_schema_registry.py::test_cli_and_mcp_schema_registry_collection_match"}
success:
  - id: SC1
    metric: "artifact registrado e consumível pelo analyzer"
    source: "testes de collector, manifesto e analyzer offline"
out_of_scope:
  - "Criar, atualizar, registrar ou excluir registry/schema/version."
  - "Provar compatibilidade funcional com produtores/consumidores sem seus artefatos."
  - "Buscar todas as versões por padrão; a coleta usa latest observado e registra o limite."
unknowns:
  - id: U1
    blocks: [AC1]
    unlock: "Permissões IAM, região e existência do registry/schema no ambiente do operador."
case_id: null
change_kinds: [tool_or_verb, dependency, knowledge_doc]
---

# STREAMING_SCHEMA_REGISTRY_COLLECTOR — requisitos

O contrato de coleta é separado do contrato de julgamento: o collector grava
metadados e a definição retornada pela API, enquanto `analyze schema-registry`
continua sendo o único caminho que emite facts e unresolved de compatibilidade.
