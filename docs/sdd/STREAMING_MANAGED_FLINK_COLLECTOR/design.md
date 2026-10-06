---
sdd: 1
feature: STREAMING_MANAGED_FLINK_COLLECTOR
phase: design
profile: dev
status: ready
upstream:
  path: docs/sdd/STREAMING_MANAGED_FLINK_COLLECTOR/define.md
  sha256: "b431e1a8f702b016c4fd1aa22d0fbc9370583d53d42d21be043134df4a94e9a8"
files:
  - {path: sparkforge_aws/collect/managed_flink.py, action: create, reason: "Cliente kinesisanalyticsv2 read-only, normalização, redaction, limites, cache e manifesto."}
  - {path: sparkforge_aws/collect/base.py, action: modify, reason: "Registrar kind managed_flink_application no contrato de artifacts."}
  - {path: sparkforge_aws/adapters/_core.py, action: modify, reason: "Adapter compartilhado de coleta e envelope de erro/cache."}
  - {path: sparkforge_aws/adapters/cli.py, action: modify, reason: "Verbo collect managed-flink."}
  - {path: sparkforge_aws/adapters/tools.py, action: modify, reason: "Tool MCP read-only de aquisição."}
  - {path: parity.yaml, action: modify, reason: "Paridade CLI/MCP/files do collector."}
  - {path: manifest.json, action: modify, reason: "Registrar nova tool MCP na superfície publicada."}
  - {path: tests/test_collect_managed_flink.py, action: create, reason: "Cliente falso, redaction, cache, analyzer e paridade."}
  - {path: knowledge/flink-streaming.md, action: modify, reason: "Procedimento Managed Flink, API observada e blind spots."}
  - {path: docs/streaming/prompt-coverage.md, action: modify, reason: "Atualizar lacuna Managed Flink com collector entregue e limites restantes."}
  - {path: docs/surface.lock.json, action: modify, reason: "Lock da superfície após nova tool."}
  - {path: knowledge/offline-manifest.json, action: modify, reason: "Hash do knowledge atualizado para o bundle offline."}
  - {path: knowledge/sources.lock.json, action: modify, reason: "Fonte oficial do DescribeApplication registrada."}
  - {path: docs/guia/referencia/README.md, action: modify, reason: "Índice gerado da referência CLI/MCP."}
  - {path: docs/guia/referencia/cli/collect.md, action: modify, reason: "Referência gerada do novo verbo collect."}
  - {path: docs/guia/referencia/tools/README.md, action: modify, reason: "Índice gerado da nova tool."}
  - {path: docs/guia/referencia/tools/sparkforge_collect_managed_flink.md, action: create, reason: "Contrato gerado da tool MCP."}
  - {path: docs/guia/03-cli.md, action: modify, reason: "Uso do verbo collect managed-flink."}
  - {path: docs/guia/04-mcp.md, action: modify, reason: "Uso MCP e limites da coleta."}
decisions:
  - id: D1
    choice: "Exigir application_name e coletar DescribeApplication com IncludeAdditionalDetails=false; normalizar apenas campos de configuração observáveis."
    rejected: ["Listar aplicações sem identidade declarada, que aumenta cardinalidade e custo sem responder qual workload investigar", "Incluir detalhes adicionais por padrão, que pode retornar job plan/código e ampliar payload sem necessidade"]
    rollback: "git revert dos commits desta feature; o dump manual e analyze flink continuam disponíveis."
  - id: D2
    choice: "Usar kind separado managed_flink_application e adaptar o payload ao namespace managed_flink existente."
    rejected: ["Reutilizar streaming_integrations, que misturaria fontes e esconderia a API específica", "Criar novo analyzer, que duplicaria facts e surface sem evidência de necessidade"]
    rollback: "git revert do collector e do registro de kind; nenhum estado AWS foi alterado."
  - id: D3
    choice: "Representar role, VPC, logging, checkpoints e paralelismo como observações escalares/contagens; não modelar ARN como connector."
    rejected: ["Inferir source/sink a partir de VPC ou CloudWatch log stream", "Preencher métricas ausentes com zero"]
    rollback: "git revert do normalizador; os unresolved do analyzer permanecem como antes."
covers:
  - {part: "collector e artifact", acceptance: [AC1, AC2]}
  - {part: "CLI/MCP e paridade", acceptance: [AC3]}
  - {part: "consumo offline pelo analyzer", acceptance: [AC4]}
---

# STREAMING_MANAGED_FLINK_COLLECTOR — desenho

```text
Managed Flink DescribeApplication (read-only)
                 |
                 v
collect managed-flink --repo ... --application-name ...
                 |
                 +--> .sparkforge_aws/artifacts/managed_flink_application/*.json
                 +--> manifest + sha256 + collect command
                 |
                 v
analyze flink --artifact managed_flink
```

O módulo de coleta importa boto3 apenas sob demanda. `ApplicationDetail` é
normalizado para o contrato já consumido por `facts.flink`; detalhes ausentes
não viram zero nem connector inventado. A documentação oficial da API v2
define `ApplicationName`, `IncludeAdditionalDetails` e os campos de runtime,
estado, versão, checkpoint, paralelismo, VPC e logging retornados pelo
`DescribeApplication`.

## Conhecimento consultado

- AWS Managed Service for Apache Flink `DescribeApplication` API v2:
  https://docs.aws.amazon.com/managed-flink/latest/apiv2/API_DescribeApplication.html
- `sparkforge-aws rules lookup --category streaming` e `knowledge/streaming/runtime-matrix.md` para manter runtime e lacunas version-aware.
