---
sdd: 1
feature: STREAMING_READ_ONLY_COLLECTORS
phase: design
profile: dev
status: ready
upstream:
  path: docs/sdd/STREAMING_READ_ONLY_COLLECTORS/define.md
  sha256: "88b0c9beff0fa5fa6e86d006d50763b1212f9fe1f3a5770c9d6c5608995f3f95"
files:
  - {path: sparkforge/collect/base.py, action: modify, reason: "registrar artifact kind streaming_integrations"}
  - {path: sparkforge/collect/streaming.py, action: create, reason: "coletar cinco fontes read-only com redaction e cache"}
  - {path: sparkforge/adapters/_core.py, action: modify, reason: "publicar wrapper comum CLI/MCP"}
  - {path: sparkforge/adapters/cli.py, action: modify, reason: "adicionar collect streaming-integrations"}
  - {path: sparkforge/adapters/tools.py, action: modify, reason: "adicionar tool MCP open-world/local mutation"}
  - {path: tests/test_collect_streaming.py, action: create, reason: "provar fakes, cache, redaction e limites"}
  - {path: knowledge/streaming-integrations.md, action: modify, reason: "documentar fronteira e coleta"}
decisions:
  - id: D1
    choice: "Usar ARTIFACT_KIND streaming_integrations e caminho determinístico por identificadores."
    rejected: ["um arquivo por serviço sem contrato composto", "estado live inferido de config"]
    rollback: "Remover o collector e preservar apenas dumps manuais do analyzer."
  - id: D2
    choice: "Usar boto3 lazy e clientes falsos nos testes."
    rejected: ["importar boto3 no core", "abrir endpoint Kafka no extrator"]
    rollback: "Desabilitar a rota live e manter o contrato offline."
  - id: D3
    choice: "Redigir secret-like keys recursivamente e preservar unresolved."
    rejected: ["persistir configuração bruta", "tratar ausência de métrica como zero"]
    rollback: "Reverter somente normalização e manter coleta limitada."
covers:
  - {part: "read-only checkpoint and AWS snapshots", acceptance: [AC1, AC2]}
  - {part: "cache and bounds", acceptance: [AC3]}
  - {part: "CLI/MCP surface", acceptance: [AC4]}
  - {part: "tests and gates", acceptance: [AC5]}
---

# STREAMING_READ_ONLY_COLLECTORS — design

Cada seção é independente. Falha de uma API ainda deve ser investigada como
erro de fronteira, enquanto ausência de métrica temporal fica no payload como
unresolved para não confundir “não coletado” com “zero”.
