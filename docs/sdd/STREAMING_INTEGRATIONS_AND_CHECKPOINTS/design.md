---
sdd: 1
feature: STREAMING_INTEGRATIONS_AND_CHECKPOINTS
phase: design
profile: dev
status: ready
upstream:
  path: docs/sdd/STREAMING_INTEGRATIONS_AND_CHECKPOINTS/define.md
  sha256: "4151e2dd6a853a6fcf51a75e01389062a46ed2666d40b13d4985782c8fada5f9"
files:
  - {path: sparkforge_aws/facts/streaming_integrations.py, action: create, reason: "extrair quatro domínios offline e redigir campos sensíveis"}
  - {path: sparkforge_aws/adapters/_core.py, action: modify, reason: "publicar analyzer determinístico"}
  - {path: sparkforge_aws/adapters/cli.py, action: modify, reason: "adicionar analyze streaming-integrations"}
  - {path: sparkforge_aws/adapters/tools.py, action: modify, reason: "adicionar MCP read-only"}
  - {path: rules/catalog/streaming-integrations.yaml, action: create, reason: "julgar quatro famílias de lacunas"}
  - {path: fixtures/streaming_integrations, action: create, reason: "goldens completo e incompleto"}
  - {path: knowledge/streaming-integrations.md, action: create, reason: "modelo e fronteira de coleta"}
  - {path: tests/test_streaming_integrations.py, action: create, reason: "golden, schema e paridade"}
  - {path: tests/test_fixtures_kind_coverage.py, action: modify, reason: "garantir kind por golden"}
decisions:
  - id: D1
    choice: "Um JSON pode declarar as quatro seções; cada domínio mantém namespace próprio."
    rejected: ["uma regra genérica por texto", "quatro analyzers que duplicam o mesmo envelope"]
    rollback: "Remover analyzer/adapters e preservar contrato como conhecimento sem mutação live."
  - id: D2
    choice: "Séries são medidas, nunca tendência inventada; menos de duas observações gera unresolved."
    rejected: ["limiar fixo sem SLO", "inferir backlog ou saúde por nome" ]
    rollback: "Reverter conclusão temporal e manter somente as medidas declaradas."
  - id: D3
    choice: "Collector live é N/A nesta wave e documentado como motivo operacional."
    rejected: ["importar cliente Kafka/AWS no core", "simular endpoint em fixture" ]
    rollback: "Adicionar collector separado somente com contrato de autorização e confirmação operacional."
covers:
  - {part: "checkpoint facts and unresolved", acceptance: [AC1]}
  - {part: "Kafka Connect and Streams facts", acceptance: [AC2, AC3]}
  - {part: "OpenLineage facts", acceptance: [AC4]}
  - {part: "CLI/MCP and regression gates", acceptance: [AC5, AC6]}
---

# STREAMING_INTEGRATIONS_AND_CHECKPOINTS — desenho

O fluxo é `JSON sanitizado → Fact → judge → Finding/unresolved`; nenhum passo
abre rede ou atribui causalidade.
