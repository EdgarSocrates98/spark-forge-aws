---
sdd: 1
feature: STREAMING_READ_ONLY_COLLECTORS
phase: define
profile: dev
status: ready
upstream:
  path: docs/sdd/STREAMING_READ_ONLY_COLLECTORS/explore.md
  sha256: "f1867dd258ae0b678aa758cc63685a3e36818b546032810eb76e0aa174816e1d"
hypothesis:
  claim: "Um coletor composto e read-only reduz blind spots operacionais sem misturar credenciais no extrator determinístico."
  prediction: "Snapshots reais redigidos entram no manifesto; segunda coleta íntegra é cache hit; limites e APIs ausentes são nomeados."
  experiment: "Fakes de boto3 para cinco fontes, teste de cache/redaction/limites, CLI/MCP e gates de superfície."
acceptance:
  - id: AC1
    statement: "Checkpoint S3 e snapshots AWS são coletados apenas por chamadas de leitura e registrados com hash."
    verified_by: {kind: test, ref: tests/test_collect_streaming.py::test_collector_composes_read_only_snapshots_and_redacts}
  - id: AC2
    statement: "Secrets são redigidos antes da escrita local e o contrato mantém unresolved temporal."
    verified_by: {kind: test, ref: tests/test_collect_streaming.py::test_collector_composes_read_only_snapshots_and_redacts}
  - id: AC3
    statement: "Hash íntegro evita rede e credenciais em repetição; limites inválidos são recusados."
    verified_by: {kind: test, ref: tests/test_collect_streaming.py::test_offline_hit_does_not_touch_aws}
  - id: AC4
    statement: "CLI e MCP expõem o mesmo coletor e preservam a classificação de mutação local/open-world."
    verified_by: {kind: test, ref: tests/test_collect_streaming.py::test_cli_parser_and_handler_are_wired}
  - id: AC5
    statement: "SDD, surface, bundle offline e regressão passam."
    verified_by: {kind: command, ref: python scripts/check_surface_lock.py}
success:
  - id: SC1
    metric: "AC1–AC5 verdes; nenhuma chamada de escrita AWS"
    source: "testes com clientes falsos e gates do repositório"
out_of_scope:
  - "Kafka Connect REST, Kafka Streams metrics e OpenLineage endpoint"
  - "CloudWatch lag/throughput, replay e benchmark temporal"
  - "qualquer alteração de estado AWS"
unknowns:
  - id: U1
    blocks: [AC5]
    unlock: "Regenerar referência MCP, surface lock, manifest/offline counts e SDD stamps."
change_kinds: [extractor, tool_or_verb, status_numbers]
---

# STREAMING_READ_ONLY_COLLECTORS — definição

O collector é uma ponte de aquisição, não um juiz. O contrato salvo continua
submetido ao analyzer offline e publica unresolved para tudo que a API não
mede.
