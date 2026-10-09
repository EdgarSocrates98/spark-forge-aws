---
sdd: 1
feature: STREAMING_MANAGED_FLINK_COLLECTOR
phase: define
profile: dev
status: ready
hypothesis:
  claim: "Uma coleta read-only de DescribeApplication transforma a configuração observada do Managed Service for Apache Flink em artifact reproduzível que o analyzer managed_flink já entende."
  prediction: "Com um nome de aplicação declarado, o collector preserva identidade, runtime, estado, versão, checkpoint, paralelismo, VPC/logging observados e limites nomeados para métricas/conectores não retornados pela API; cache local não chama AWS novamente."
  experiment: "Executar collector com cliente kinesisanalyticsv2 falso, analisar o artifact com artifact=managed_flink e repetir a coleta a partir do cache."
acceptance:
  - id: AC1
    statement: "O collector chama apenas DescribeApplication read-only, normaliza o retorno em application/configuration e preserva unresolved quando métricas ou conectores não são observáveis."
    verified_by: {kind: test, ref: "tests/test_collect_managed_flink.py::test_collector_normalizes_describe_response"}
  - id: AC2
    statement: "O artifact registrado possui kind managed_flink_application, manifesto, SHA, comando de coleta, redaction e cache offline-first."
    verified_by: {kind: test, ref: "tests/test_collect_managed_flink.py::test_collector_cache_is_offline_and_manifested"}
  - id: AC3
    statement: "CLI e MCP expõem a mesma coleta read-only com aplicação, região e now declarados."
    verified_by: {kind: test, ref: "tests/test_collect_managed_flink.py::test_cli_and_mcp_managed_flink_collection_match"}
  - id: AC4
    statement: "O artifact coletado alimenta o analyzer managed_flink sem misturar fatos flink upstream."
    verified_by: {kind: test, ref: "tests/test_collect_managed_flink.py::test_collected_artifact_feeds_managed_flink_analyzer"}
success:
  - id: SC1
    metric: "artifact Managed Flink registrado e analisável offline"
    source: "tests/test_collect_managed_flink.py e manifesto gerado pelo collector"
out_of_scope:
  - "Start, stop, update, delete, restore, snapshot creation ou qualquer mutação AWS."
  - "Job plan, application code, métricas CloudWatch, IAM efetivo e latência temporal; a coleta destas evidências fica unresolved e exige artefato/collector dedicado."
  - "Inferir conectores a partir de ARN de VPC, logging ou role."
unknowns:
  - id: U1
    blocks: [AC1, AC4]
    unlock: "Permissão kinesisanalytics:DescribeApplication e existência da aplicação no ambiente do operador."
  - id: U2
    blocks: [AC1]
    unlock: "Job plan ou métricas observadas em artifact próprio; DescribeApplication sem IncludeAdditionalDetails não responde essas perguntas."
case_id: null
change_kinds: [tool_or_verb, knowledge_doc]
---

# STREAMING_MANAGED_FLINK_COLLECTOR — requisitos

O collector adquire somente a descrição declarada pela API v2 do Managed Service
for Apache Flink. O contrato de coleta preserva ausência como unresolved; o
analyzer e o judge continuam sendo os caminhos de facts e findings.
