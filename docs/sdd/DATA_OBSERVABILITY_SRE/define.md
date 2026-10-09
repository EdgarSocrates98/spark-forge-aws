---
sdd: 1
feature: DATA_OBSERVABILITY_SRE
phase: define
profile: dev
status: ready
upstream:
  path: docs/sdd/DATA_OBSERVABILITY_SRE/explore.md
  sha256: "5549d8f888a085add26fc0fb430357cc5d78c5d09ddb4417922f13b6f421e335"
hypothesis:
  claim: "Um avaliador offline de SLOs transforma métricas exportadas em status, error budget e saúde de dependências sem ocultar ausência de evidência."
  prediction: "Medições de freshness, completeness, latency, lag, throughput e availability produzem avaliação determinística; SLO sem medição, unidade ou objetivo vira unresolved."
  experiment: "Carregar fixture OTel-like com SLOs, medições, dependências e incidentes pelo CLI/MCP."
acceptance:
  - id: AC1
    statement: "O avaliador calcula conformidade e error budget somente para medições numéricas compatíveis e registra SLO sem evidência como unresolved."
    verified_by: {kind: test, ref: "tests/test_data_observability.py::test_observability_evaluates_slos_and_error_budget"}
  - id: AC2
    statement: "O relatório preserva dependências, blast radius declarado e MTTR de incidentes encerrados sem consultar o ambiente."
    verified_by: {kind: test, ref: "tests/test_data_observability.py::test_observability_preserves_incidents_dependencies_and_blast_radius"}
  - id: AC3
    statement: "CLI e MCP expõem o mesmo envelope de observabilidade."
    verified_by: {kind: command, ref: "python -m sparkforge_aws.adapters.cli analyze data-observability --path fixtures/observability/sre.yaml"}
success:
  - id: SC1
    metric: "Métricas sem observação retornam unresolved e não status met"
    source: "campo unresolved do relatório"
out_of_scope:
  - "Consulta direta a Prometheus, CloudWatch, OpenTelemetry Collector ou PagerDuty."
  - "Alegar disponibilidade histórica quando janela ou timestamps faltarem."
unknowns:
  - id: U1
    blocks: [AC3]
    unlock: "Registrar surface lock e referência gerada após adicionar o tool."
case_id: null
change_kinds: [extractor, tool_or_verb, knowledge_doc]
---

# DATA_OBSERVABILITY_SRE — requisitos

Unidades, operador (`gte`, `lte`) e janela pertencem ao SLO. A camada não
atribui causa a violação: ela apenas relata medida, regra declarada e lacunas.
