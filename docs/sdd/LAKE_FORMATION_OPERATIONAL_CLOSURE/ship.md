---
sdd: 1
feature: LAKE_FORMATION_OPERATIONAL_CLOSURE
phase: ship
profile: dev
status: done
upstream:
  path: docs/sdd/LAKE_FORMATION_OPERATIONAL_CLOSURE/build_report.md
  sha256: "bd520aae1b94d1148f61fde6cfa93f4f324497503582bd1b48e3a95f49ac0552"
hypothesis_outcome: confirmed
registries: [offline_manifest, sources_lock, sync_skills, agents_parity, surface_lock, generated_reference, claims_gate]
deviations:
  - "T3 do plano permaneceu skipped como implementação: os contratos de preflight, performance/FinOps e cross-review já estavam compostos e foram preservados por testes de guarda, conforme o build_report."
  - "A execução local adicional da receita de lotes foi interrompida após o lote a-c (2506 passed, 2 skipped); o ship não usa essa tentativa como prova de suíte completa. Nenhum arquivo de produção ou AWS foi alterado durante o ship."
---

# LAKE_FORMATION_OPERATIONAL_CLOSURE — entrega

## Hipótese

Confirmada. O experimento foi executado sobre o decision engine offline existente:
os testes acceptance cobrem revisão de PySpark/Terraform, configuração tardia,
camadas metadata/data/credential, taxonomia e root cause, migração version-aware,
preflight least-privilege, progressive disclosure, paridade CLI/MCP e documentação.
Os números de performance e custo continuam condicionais e sem claim, porque não
houve benchmark AWS nem DPUSeconds observado nesta feature.

## Gates rodados

- `python -m pytest -p no:cacheprovider --basetemp E:\pytest-lf-op tests/test_lakeformation_operational_closure.py -q` (exit 0; 8 passed)
- `python -m pytest -p no:cacheprovider --basetemp E:\pytest-lf-arch tests/test_lakeformation_architecture.py -q` (exit 0; 13 passed)
- `python -m pytest -p no:cacheprovider --basetemp E:\pytest-lf-fta tests/test_lakeformation_fgac_fta_improvements.py tests/test_lakeformation_access_graph.py tests/test_lakeformation_engine.py -q` (exit 0; 34 passed)
- `python -m pytest -p no:cacheprovider --basetemp E:\pytest-gap-a tests/test_lakeformation_fgac_fta_improvements.py::test_capability_statuses_are_enforced tests/test_lakeformation_fgac_fta_improvements.py::test_source_and_target_are_evaluated_independently tests/test_lakeformation_fgac_fta_improvements.py::test_cross_account_resolution_modes tests/test_lakeformation_fgac_fta_improvements.py::test_hybrid_access_is_governance_aware tests/test_lakeformation_fgac_fta_improvements.py::test_glue4_current_architecture_is_not_migration -q` (exit 0; 5 passed)
- `python -m pytest -p no:cacheprovider --basetemp E:\pytest-gap-b tests/test_lakeformation_architecture.py::test_read_and_write_authorization_are_separate tests/test_lakeformation_architecture.py::test_cross_account_governance_requires_independent_evidence tests/test_lakeformation_architecture.py::test_golden_path_glue51_cross_account_iceberg tests/test_lakeformation_architecture.py::test_negative_scenarios_fail_closed -q` (exit 0; 4 passed)
- `python scripts/sync_skills.py --check` (exit 0)
- `python -m pytest -p no:cacheprovider --basetemp E:\pytest-ref tests/test_reference_docs.py -q` (exit 0; 5 passed)
- `python scripts/gen_reference_docs.py` (exit 0; 242 páginas, 0 regravadas, 0 removidas)
- `python scripts/check_surface_lock.py` (exit 0)
- `python scripts/check_vnext_claims.py` (exit 0)
- `python scripts/check_status_numbers.py --strict` (exit 0)
- `python scripts/verify_offline_bundle.py` (exit 0; 58 arquivos)
- `python -m pytest -p no:cacheprovider --basetemp E:\pytest-lf-knowledge tests/test_offline_expansion.py tests/test_refresh_knowledge.py -q` (exit 0; 43 passed)
- `python -m pytest -p no:cacheprovider --basetemp E:\pytest-batches tests/test_suite_batches.py -q` (exit 0; 4 passed)
- `python -m pytest -p no:cacheprovider --basetemp E:\pytest-sdd tests/test_sdd.py -q` (exit 0; 165 passed)
- `sparkforge-aws sdd check --repo . --feature LAKE_FORMATION_OPERATIONAL_CLOSURE` (exit 0; sem recusas ou lacunas)

## Checklist da revisão contra a main `8b8fb54a`

- `not_supported` bloqueia: `test_capability_statuses_are_enforced` exige
  `status: blocked` e `CAPABILITY-NOT-SUPPORTED`; `read_only` também bloqueia
  escrita e `limited/version_dependent` permanece unresolved sem prova específica.
- Source e target são independentes: `test_source_and_target_are_evaluated_independently`
  valida formato, operação e capability por perna.
- Cross-account não exige resource link universalmente:
  `explicit_catalog_id` fecha a rota Glue ETL e não adiciona `resource_link` à
  verificação obrigatória; rota ausente permanece unresolved.
- Hybrid Access é governança separada de FGAC/FTA:
  `IAMAllowedPrincipals` não bloqueia o caso híbrido completo; ausência de
  opt-in/versionamento mantém o caso unresolved.
- Glue 4.0 corrente não vira migração sem alvo: o teste corrente não emite
  `GLUE-LF-MIGRATION`; a mesma arquitetura só exige migração quando há
  `migration.to_runtime` declarado.

## Pendências honestas

- Nenhuma capability futura é promovida por analogia. Células sem fonte fechada
  continuam `unknown` ou `version_dependent`.
- RAM, IAM, Lake Formation, KMS e CloudTrail continuam fatos de entrada/collect,
  não simulações ou mutações feitas pelo analyzer.
- Comparação de performance, custo e economia de tokens permanece pendente de
  runs medidos; a saída apenas declara medidas necessárias.

## Lições

- O build já havia composto preflight e cross-review antes da tarefa T3; registrar
  guardas de regressão explicitamente evita duplicar uma implementação sem teste
  vermelho honesto.
- O ship precisa registrar a receita executável de lotes e não apenas dizer que a
  suíte completa passou; `tests/test_suite_batches.py` mantém essa cobertura.
- O próximo delta deve introduzir novos collectors/facts antes de ampliar agentes
  ou declarar suporte para outra combinação de runtime, formato e operação.
