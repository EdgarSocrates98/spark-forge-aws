---
sdd: 1
feature: GLUE_DQ_ADVANCED_GOVERNANCE_GAPS
phase: define
profile: dev
status: ready
hypothesis:
  claim: "Estados explícitos para controles de amostragem, geografia e autorização fecharão as lacunas de governança sem fabricar evidência."
  prediction: "As novas fixtures produzirão findings somente para controle incompleto, fronteira proibida/não comprovada e autorização incompleta; payloads com rows continuarão recusados e o report manterá provider_calls=0 e row_payloads=0."
  experiment: "Adicionar os testes DQ AI de normalização, assessment, regras e report; rodar os lotes DQ AI, catálogo/reachability, fontes/offline e a verificação de wheel."
acceptance:
  - id: AC1
    statement: "ADVANCED distingue controle completo de workgroup/bucket/retenção não observado e preserva referência documental sem promovê-la a fato."
    verified_by: {kind: test, ref: "tests/test_dq_ai_unit.py::test_sampling_controls_keep_documented_defaults_unobserved"}
  - id: AC2
    statement: "Diferença de Region não é confundida com fronteira geográfica; status proibido gera finding e status ausente permanece unresolved."
    verified_by: {kind: test, ref: "tests/test_dq_ai_unit.py::test_geographic_boundary_is_distinct_from_cross_region"}
  - id: AC3
    statement: "KMS, key policy, runtime role e Lake Formation são evidências separadas e autorização incompleta gera finding."
    verified_by: {kind: test, ref: "tests/test_dq_ai_security.py::test_authorization_requires_all_external_evidence_parts"}
  - id: AC4
    statement: "Claims AWS, contexto Iceberg/migração e variabilidade aparecem como documentação/contexto, não como medição ou provider call."
    verified_by: {kind: test, ref: "tests/test_dq_ai_report.py::test_report_exposes_documented_claims_and_risk_context"}
  - id: AC5
    statement: "O extrator rejeita rows e a suíte golden cobre as três regras novas."
    verified_by: {kind: test, ref: "tests/test_fixtures_golden_dq_ai.py::test_every_dq_ai_fixture_matches_declared_kinds_and_rules"}
success:
  - id: SC1
    metric: "Grupos de lacuna representados por status determinístico"
    source: "tests/test_dq_ai_unit.py e tests/test_dq_ai_security.py"
  - id: SC2
    metric: "Regras novas alcançáveis e cobertas por golden"
    source: "tests/test_fixtures_golden_dq_ai.py e tests/test_rules_catalog_reachability.py"
  - id: SC3
    metric: "Chamadas de provider e payloads de rows no report"
    source: "tests/test_dq_ai_security.py::test_assessment_never_calls_provider_or_carries_rows"
out_of_scope:
  - "Chamadas ou provisionamento de Glue, Athena, Bedrock, IAM, Lake Formation, KMS ou Terraform."
  - "Geração de DQDL ou transporte de linhas reais."
  - "Score numérico de variabilidade, custo ou ganho sem medição."
  - "Alterar semântica das regras SF-DQ-AI-001 a SF-DQ-AI-005."
unknowns:
  - id: U1
    blocks: [AC3]
    unlock: "Facts externos de IAM/Lake Formation/KMS podem ser compostos quando seus verbs já os extraírem; neste patch o desbloqueio é um manifesto metadata-only."
  - id: U2
    blocks: [AC4]
    unlock: "Fonte oficial lockada em knowledge/glue/dq-advanced-matrix.yaml; ausência de evidência do ambiente continua declarada."
change_kinds: [rule, rule_runtime_scope, extractor, knowledge_doc, fixture_corpus]
---

# GLUE_DQ_ADVANCED_GOVERNANCE_GAPS — requisitos

## Problema

O primeiro pacote não modela com precisão workgroup/bucket/retenção, claims documentais, fronteira geográfica, cadeia de autorização nem contexto Iceberg/migração. O follow-up torna cada blind spot explícito e auditável sem ampliar o boundary offline.

## Escopo de implementação

O extrator normaliza campos opcionais e rejeita rows; o assessment compõe status; o catálogo adiciona `SF-DQ-AI-006` (sampling), `SF-DQ-AI-007` (geography) e `SF-DQ-AI-008` (authorization); a matriz e o report preservam referência versus observação. Não há provider call.
