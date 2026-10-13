---
sdd: 1
feature: STREAMING_SCHEMA_REGISTRY_COLLECTOR
phase: design
profile: dev
status: ready
upstream:
  path: docs/sdd/STREAMING_SCHEMA_REGISTRY_COLLECTOR/define.md
  sha256: "49145bfd4a15d5d777a115ae5ea61b56faadb91ffe9e0cc4831e5f41ab9a2fef"
files:
  - {path: sparkforge_aws/collect/schema_registry.py, action: create, reason: "Cliente read-only, paginação, redaction, limite e artifact registrado."}
  - {path: sparkforge_aws/adapters/_core.py, action: modify, reason: "Adapter compartilhado CLI/MCP para coleta."}
  - {path: sparkforge_aws/adapters/cli.py, action: modify, reason: "Verbo collect schema-registry."}
  - {path: sparkforge_aws/adapters/tools.py, action: modify, reason: "Tool MCP agrupada por objetivo de aquisição."}
  - {path: parity.yaml, action: modify, reason: "Paridade declarada do collector."}
  - {path: tests/test_collect_schema_registry.py, action: create, reason: "Clientes falsos, cache, manifesto, CLI/MCP."}
  - {path: knowledge/schema-registry-data-contracts.md, action: modify, reason: "Procedimento de coleta, APIs e limites."}
  - {path: docs/guia/03-cli.md, action: modify, reason: "Uso do collector e segurança."}
  - {path: docs/guia/04-mcp.md, action: modify, reason: "Uso MCP e economia de surface."}
decisions:
  - id: D1
    choice: "A entrada requer registry_name ou schema_arn; schema_name filtra o registry e ausência de schema name lista schemas até max_schemas."
    rejected: ["descoberta sem limite", "inferir registry a partir de ARN parcial"]
    rollback: "git revert dos commits desta feature; nenhum estado AWS foi alterado."
  - id: D2
    choice: "Somente latest schema version é buscada por schema; definições acima do limite são omitidas com unresolved, nunca truncadas."
    rejected: ["truncar definição silenciosamente", "baixar histórico inteiro por padrão"]
    rollback: "git revert do collector; reanálise de dumps manuais continua disponível."
covers:
  - {part: "read-only collector", acceptance: [AC1, AC2]}
  - {part: "CLI/MCP parity", acceptance: [AC3]}
---

# STREAMING_SCHEMA_REGISTRY_COLLECTOR — desenho

```text
AWS Glue Schema Registry (list/get)
              |
              v
collect schema-registry --repo ...
              |
              +--> .sparkforge_aws/artifacts/schema_registry/*.json
              +--> manifest + sha256 + collect command
              |
              v
analyze schema-registry --path artifact
```

O core não importa boto3 e o collector não chama operações de escrita.
Identidade, status, formato, compatibilidade e definição são preservados como
observações; ausência de permissão, schema, versão ou definição permanece
unresolved.
