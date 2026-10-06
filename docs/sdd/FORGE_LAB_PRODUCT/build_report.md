---
sdd: 1
feature: FORGE_LAB_PRODUCT
phase: build_report
profile: dev
status: done
upstream:
  path: docs/sdd/FORGE_LAB_PRODUCT/plan.md
  sha256: "4016d009bf7fc49b98ca414c3b562366e45f8fc0fa6c6d0691099bd01a19f14b"
tasks:
  - id: T1
    status: skipped
  - id: T2
    status: skipped
  - id: T3
    status: skipped
  - id: T4
    status: skipped
  - id: T5
    status: skipped
  - id: T6
    status: skipped
claims:
  - text: "Registry único, fidelidade L0-L3, profiles, modes, versões sem latest e schemas canônicos estão declarados e validados offline."
    evidence_ref: "tests/test_forge_lab_product.py::test_registry_and_scenario_contracts_are_pinned"
  - text: "Golden 20 é DSL declarativa e compila para actions allowlisted reutilizáveis por Compose e Testcontainers."
    evidence_ref: "tests/test_forge_lab_product.py::test_golden_scenarios_compile_to_reusable_actions"
  - text: "Backends compartilham plano e mutações exigem execute e confirm, com contrato AWS L3 separado e sem cliente AWS no core offline."
    evidence_ref: "tests/test_forge_lab_product.py::test_runtime_backends_share_plan_and_mutations_are_guarded"
  - text: "Receipt, oracle independente, captura de evidências e equivalência multi-engine preservam fatos observados sem inventar performance."
    evidence_ref: "tests/test_forge_lab_product.py::test_receipt_oracle_and_equivalence_are_independent"
  - text: "Ciclo operacional Forge Lab está exposto na CLI top-level e sua documentação explicita limites de fidelidade."
    evidence_ref: "tests/test_forge_lab_product.py::test_cli_exposes_lab_product_commands"
change_id: null
---

# FORGE_LAB_PRODUCT — relatório do build

## Entrega

As seis tarefas do plano foram implementadas em commits separados: contratos e
registry; DSL, generators e faults; runtime guardado e doctor; evidence/oracle;
CLI; documentação e referência gerada. O produto permanece CLI-first, offline
por default e sem subir Docker ou acessar AWS durante análise, planejamento,
doctor e verificação.

## Desvio de execução dos testes

As tarefas T1–T6 estão `skipped` no bloco de red/green porque o operador exigiu
que nenhuma suíte fosse executada até o fechamento de todas as fases. Não há
vermelho histórico honesto para declarar depois da implementação. Os testes
focados foram escritos durante o plano e serão executados como validação final,
antes do ship, junto com as suítes do repositório.

## Verificações offline já executadas

- `python -m py_compile` nos módulos novos e no adaptador CLI — exit 0.
- `python scripts/gen_reference_docs.py` — referência CLI regenerada.
- `python scripts/check_surface_lock.py --update` — superfície sem divergência.
- `sparkforge-aws sdd check --repo . --feature FORGE_LAB_PRODUCT` — estrutura upstream válida.

Nenhum runtime L1/L2 foi iniciado neste build; imagens, digests e disponibilidade
do host permanecem evidência dependente de `lab doctor`/execução explícita.
