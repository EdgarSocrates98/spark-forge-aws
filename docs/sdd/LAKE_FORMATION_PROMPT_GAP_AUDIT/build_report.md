---
sdd: 1
feature: LAKE_FORMATION_PROMPT_GAP_AUDIT
phase: build_report
profile: dev
status: done
upstream:
  path: docs/sdd/LAKE_FORMATION_PROMPT_GAP_AUDIT/plan.md
  sha256: "06a8fb5c2ce824fd4d53a764885b170043225241065a0d17d571eeea40aff16f"
tasks:
  - id: T1
    status: done
    red: {command: "pytest --basetemp .pytest-temp tests/test_lakeformation_prompt_acceptance.py -q", exit: 1}
    green: {command: "pytest --basetemp .pytest-temp tests/test_lakeformation_prompt_acceptance.py -q", exit: 0}
  - id: T2
    status: done
    red: {command: "pytest --basetemp .pytest-temp tests/test_lakeformation_prompt_acceptance.py -q", exit: 1}
    green: {command: "pytest --basetemp .pytest-temp tests/test_lakeformation_prompt_acceptance.py -q", exit: 0}
  - id: T3
    status: skipped
claims:
  - text: "A matriz final executa Glue FTA Parquet, Glue 4 corrente, EMR Serverless/resource-link, EMR FTA cross-account, Hybrid, LF-TBAC/RAM, versão cross-account mais nova e DML EMR sem célula como unresolved."
    evidence_ref: "tests/test_lakeformation_prompt_acceptance.py::test_prompt_final_knowledge_matrix_is_executable"
  - text: "Os cinco gaps críticos têm regressões determinísticas no decision engine."
    evidence_ref: "tests/test_lakeformation_prompt_acceptance.py::test_prompt_critical_gap_regressions"
  - text: "O migration report publica as seções exigidas pelo prompt sem inferir custo ou suporte."
    evidence_ref: "tests/test_lakeformation_prompt_acceptance.py::test_migration_report_has_prompt_sections"
  - text: "A documentação e os mirrors mantêm o contrato de disclosure e os runbooks finais."
    evidence_ref: "tests/test_lakeformation_prompt_acceptance.py::test_prompt_acceptance_audit_is_complete"
change_id: null
---

# LAKE_FORMATION_PROMPT_GAP_AUDIT — relatório do build

## Red/green

O focused acceptance foi executado antes da implementação nova e falhou por
quatro lacunas observáveis: referência de runtime EMR ausente, matriz Glue 4
com expectativa de status incorreta para evidência incompleta e ausência de
`migration.sections`. Depois do núcleo, a mesma suíte passou com 16 testes.

As regressões dos cinco gaps críticos passaram no estado final: são guards de
comportamento já corrigido pela feature anterior, não uma autorização para
relaxar o decision engine.

## Gates executados

- `pytest --basetemp .pytest-temp tests/test_lakeformation_prompt_acceptance.py -q` — exit 0; 16 passed.
- `pytest --basetemp .pytest-temp tests/test_lakeformation_architecture.py tests/test_lakeformation_fgac_fta_improvements.py tests/test_lakeformation_prompt_acceptance.py -q` — exit 0; 37 passed.
- `ruff check sparkforge_aws/lakeformation/architecture.py tests/test_lakeformation_prompt_acceptance.py` — exit 0.
- `python scripts/verify_offline_bundle.py --repo .` — exit 0; 58 checked.
- `python scripts/sync_skills.py --check` — exit 0.
- `python scripts/gen_reference_docs.py --check` — exit 0.
- `python scripts/check_surface_lock.py` — exit 0.
- `python scripts/check_status_numbers.py --strict` — exit 0.
- `pytest --basetemp E:\pytest-sf-temp tests/test_vnext_claims.py::TestGateReal::test_o_manifesto_do_repositorio_esta_consistente -q` — exit 0.
- `sparkforge-aws sdd check --repo . --feature LAKE_FORMATION_PROMPT_GAP_AUDIT` — exit 0.

## Limites e desvios

Não houve coleta ou mutação AWS, benchmark, DPUSeconds, CloudTrail, IAM,
grants, RAM, KMS ou medição de tokens. A auditoria completa de proofs do gate
de claims foi interrompida por duração; a consistência estrutural e o teste do
manifesto passaram, e o CI do PR executa os gates amplos. O lote completo da
suíte não foi repetido por orientação do operador.
