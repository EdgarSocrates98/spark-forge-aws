---
sdd: 1
feature: OPEN_LAKEHOUSE_CATALOG
phase: define
profile: dev
status: ready
upstream:
  path: docs/sdd/OPEN_LAKEHOUSE_CATALOG/explore.md
  sha256: "e1a9077b46d03fc883593b74835d3ad17bf44ab215690e374b826fa271e5fda0"
hypothesis:
  claim: "Um contrato comum de catalog topology permite avaliar lakehouse aberto e bindings engine-table sem presumir capacidades."
  prediction: "O analisador retorna catalogs, engines, tables, bindings, capabilities declaradas e unresolved para referência desconhecida ou binding sem evidência."
  experiment: "Carregar fixture multi-catalog e conferir fingerprint, ordenação e unresolved por CLI/MCP."
acceptance:
  - id: AC1
    statement: "O contrato valida catalogs, engines, tabelas e bindings explícitos, sem guardar credenciais."
    verified_by: {kind: test, ref: "tests/test_lakehouse_catalog.py::test_lakehouse_catalog_contract_is_deterministic"}
  - id: AC2
    statement: "CLI e MCP retornam a mesma topologia e marcam integração desconhecida como unresolved."
    verified_by: {kind: command, ref: "python -m sparkforge_aws.adapters.cli analyze lakehouse-catalog --path fixtures/platform/catalog.yaml"}
success:
  - id: SC1
    metric: "Fingerprint estável e zero segredo nos registros normalizados"
    source: "saída do analisador e fixture versionada"
out_of_scope:
  - "Negociar protocolo live ou validar compatibilidade de uma versão sem dump/evidence."
  - "Criar/deletar catalog, tabela, bucket, namespace ou grant."
unknowns:
  - id: U1
    blocks: [AC2]
    unlock: "Adicionar fragments coletados por serviço com evidence e versão detectada."
case_id: null
change_kinds: [extractor, tool_or_verb, knowledge_doc]
---

# OPEN_LAKEHOUSE_CATALOG — requisitos

O contrato separa identidade do catalog, capabilities declaradas, engines
consumidoras e tabela. Secrets, tokens e endpoints privados são recusados ou
substituídos por referência não sensível.
