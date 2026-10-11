---
sdd: 1
feature: FORGE_PORTAL
phase: plan
profile: dev
status: ready
upstream:
  path: docs/sdd/FORGE_PORTAL/design.md
  sha256: "af7089479ab4eb3261b501793712ff6ebef34119074995792e31f91b55024fcb"
tasks:
  - id: T1
    files: ["sparkforge_aws/_forge_portal.py", "portal/assets/"]
    covers: ["AC1", "AC5"]
    test: {path: "tests/test_portal_adapter.py", name: "test_bootstrap_workspace_vazio"}
  - id: T2
    files: ["sparkforge_aws/portal_adapter.py"]
    covers: ["AC2", "AC3", "AC4"]
    test: {path: "tests/test_portal_adapter.py", name: "test_install_plan_apply_verified"}
  - id: T3
    files: ["sparkforge_aws/adapters/cli.py"]
    covers: ["AC1"]
    test: {path: "tests/test_portal_adapter.py", name: "test_portal_verb_parseia"}
  - id: T4
    files: ["tests/test_portal_adapter.py"]
    covers: ["AC2", "AC3", "AC4", "AC6"]
    test: {path: "tests/test_portal_adapter.py", name: "test_task_intencao_ambigua_recusa_nomeada"}
  - id: T5
    files: ["pyproject.toml", "docs/reference/command-rationale.json", "docs/learn/recipes/portal.md", "README.md", "docs/learn/README.md"]
    covers: ["AC5"]
    test: {path: "tests/test_portal_adapter.py", name: "test_assets_index_resolvido"}
---

# FORGE_PORTAL — plano

Ordem executada: T1→T5, validação por teste novo + E2E HTTP real em
workspace scratch (instalar → verificar → primeira tarefa).
