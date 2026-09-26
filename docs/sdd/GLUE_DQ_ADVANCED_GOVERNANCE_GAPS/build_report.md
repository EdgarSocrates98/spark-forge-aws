---
sdd: 1
feature: GLUE_DQ_ADVANCED_GOVERNANCE_GAPS
phase: build_report
profile: dev
status: done
upstream:
  path: docs/sdd/GLUE_DQ_ADVANCED_GOVERNANCE_GAPS/plan.md
  sha256: "cbe879d727698e43ee51a92c30f2e81b3eb80fe098ed9949bdd8650e99ef2e87"
tasks:
  - id: T1
    status: done
    red: {command: "python -m pytest --basetemp=E:/projetos/spark-forge-aws/.pytest-tmp-gaps tests/test_dq_ai_unit.py::test_sampling_controls_keep_documented_defaults_unobserved tests/test_dq_ai_unit.py::test_geographic_boundary_is_distinct_from_cross_region -q", exit: 1}
    green: {command: "python -m pytest --basetemp=E:/projetos/spark-forge-aws/.pytest-tmp-gaps tests/test_dq_ai_unit.py::test_sampling_controls_keep_documented_defaults_unobserved tests/test_dq_ai_unit.py::test_geographic_boundary_is_distinct_from_cross_region -q", exit: 0}
  - id: T2
    status: done
    red: {command: "python -m pytest --basetemp=E:/projetos/spark-forge-aws/.pytest-tmp-gaps tests/test_dq_ai_security.py::test_authorization_requires_all_external_evidence_parts -q", exit: 1}
    green: {command: "python -m pytest --basetemp=E:/projetos/spark-forge-aws/.pytest-tmp-gaps tests/test_dq_ai_security.py::test_authorization_requires_all_external_evidence_parts -q", exit: 0}
  - id: T3
    status: done
    red: {command: "python -m pytest --basetemp=E:/projetos/spark-forge-aws/.pytest-tmp-gaps tests/test_dq_ai_report.py::test_report_exposes_documented_claims_and_risk_context -q", exit: 1}
    green: {command: "python -m pytest --basetemp=E:/projetos/spark-forge-aws/.pytest-tmp-gaps tests/test_dq_ai_report.py::test_report_exposes_documented_claims_and_risk_context -q", exit: 0}
  - id: T4
    status: done
    red: {command: "python -m pytest --basetemp=E:/projetos/spark-forge-aws/.pytest-tmp-gaps tests/test_fixtures_golden_dq_ai.py::test_every_dq_ai_fixture_matches_declared_kinds_and_rules -q", exit: 1}
    green: {command: "python -m pytest --basetemp=E:/projetos/spark-forge-aws/.pytest-tmp-gaps tests/test_fixtures_golden_dq_ai.py::test_every_dq_ai_fixture_matches_declared_kinds_and_rules -q", exit: 0}
claims:
  - text: "Sampling e geografia têm estados determinísticos distintos; referência documental não é promovida a observação."
    evidence_ref: "tests/test_dq_ai_unit.py::test_sampling_controls_keep_documented_defaults_unobserved"
  - text: "A autorização Advanced exige evidência separada para KMS, key policy, runtime role e Lake Formation."
    evidence_ref: "tests/test_dq_ai_security.py::test_authorization_requires_all_external_evidence_parts"
  - text: "Claims de provider, risco, Iceberg, migração e variabilidade qualitativa aparecem no report sem score numérico nem provider call."
    evidence_ref: "tests/test_dq_ai_report.py::test_report_exposes_documented_claims_and_risk_context"
  - text: "Fixtures cobrem cenário completo, fronteira geográfica unresolved, autorização incompleta e contexto de risco; rows continuam fora do contrato."
    evidence_ref: "tests/test_fixtures_golden_dq_ai.py::test_every_dq_ai_fixture_matches_declared_kinds_and_rules"
change_id: null
---

# GLUE_DQ_ADVANCED_GOVERNANCE_GAPS — relatório do build

## Desvios do plano

- O harness de mutação de thresholds exige `subject` em todo fato esperado. Os 12
  goldens DQ-AI existentes e novos receberam o subject metadata-only mínimo; isso
  não altera a asserção de kinds e mantém o contrato de rejeição de rows.
- O gate de thresholds foi executado em lote separado dos gates de regras/agentes,
  pois o comando completo excede o tempo operacional de uma chamada. Resultado:
  675 passed.
- O parser de fontes exigiu o cabeçalho `## Fontes` e URLs nuas na matriz Markdown;
  a documentação foi ajustada e o lock regenerado offline.

## Gates e revisão

- DQ-AI unit/security/report/golden: 11 passed.
- Catálogo, reachability, engine, result axis: 800 passed.
- Agentes, router, docs, fixture coverage e refresh knowledge: 225 passed.
- Threshold mutation, rule scope e runtime Glue: 675 passed.
- Offline bundle: verificado com 57 entradas.
- Revisão final de especificação e qualidade: conforme ao define/design; nenhuma
  chamada de provider, payload de rows, geração de DQDL ou score numérico foi
  introduzido.
