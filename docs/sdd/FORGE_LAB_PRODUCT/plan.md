---
sdd: 1
feature: FORGE_LAB_PRODUCT
phase: plan
profile: dev
status: ready
upstream:
  path: docs/sdd/FORGE_LAB_PRODUCT/design.md
  sha256: "974078a3e348f96cbab436fa3761e27c52903547627400782c67ec69692704da"
tasks:
  - id: T1
    files: [sparkforge/lab/contract.py, lab/versions.yaml, lab/contracts/, labs/forge-lab/lab.yaml, tests/test_forge_lab_product.py]
    covers: [AC1]
    test: {path: tests/test_forge_lab_product.py, name: test_registry_and_scenario_contracts_are_pinned}
  - id: T2
    files: [sparkforge/lab/scenario.py, sparkforge/lab/generators.py, sparkforge/lab/workload.py, sparkforge/lab/faults.py, lab/scenarios/, lab/generators/, tests/test_forge_lab_product.py]
    covers: [AC2]
    test: {path: tests/test_forge_lab_product.py, name: test_golden_scenarios_compile_to_reusable_actions}
  - id: T3
    files: [sparkforge/lab/runtime.py, sparkforge/lab/doctor.py, sparkforge/lab/aws.py, labs/forge-lab/compose.yaml, lab/compose/, tests/test_forge_lab_product.py]
    covers: [AC1, AC3]
    test: {path: tests/test_forge_lab_product.py, name: test_runtime_backends_share_plan_and_mutations_are_guarded}
  - id: T4
    files: [sparkforge/lab/evidence.py, sparkforge/lab/compatibility.py, lab/probes/, tests/test_forge_lab_product.py]
    covers: [AC4]
    test: {path: tests/test_forge_lab_product.py, name: test_receipt_oracle_and_equivalence_are_independent}
  - id: T5
    files: [sparkforge/lab/cli.py, sparkforge/lab/__init__.py, sparkforge/adapters/cli.py, tests/test_forge_lab_product.py]
    covers: [AC5]
    test: {path: tests/test_forge_lab_product.py, name: test_cli_exposes_lab_product_commands}
  - id: T6
    files: [docs/knowledge/forge-lab-product.md, lab/contracts/, labs/forge-lab/README.md]
    covers: [AC1, AC2, AC3, AC4, AC5]
    test: {path: tests/test_forge_lab_product.py, name: test_lab_documentation_states_fidelity_boundaries}
---

# FORGE_LAB_PRODUCT — plano

Cada tarefa terá teste escrito antes da implementação. Por instrução do
operador, os testes ficam sem execução até T6 e a suíte completa roda somente
depois de todas as fases; comandos offline e `py_compile` podem ser usados para
detectar erros de sintaxe.

## Sequência de commits

1. `feat(lab): add forge lab foundation contracts`
2. `feat(lab): add scenario compiler and deterministic generators`
3. `feat(lab): add guarded runtime and lab doctor`
4. `feat(lab): add evidence capture oracle and compatibility`
5. `feat(lab): expose forge lab cli lifecycle`
6. `docs(lab): document forge lab product contract`
