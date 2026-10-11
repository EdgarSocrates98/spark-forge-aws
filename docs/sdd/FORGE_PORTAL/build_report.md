---
sdd: 1
feature: FORGE_PORTAL
phase: build_report
profile: dev
status: ready
upstream:
  path: docs/sdd/FORGE_PORTAL/plan.md
  sha256: "dd6217069257790fdfa75e1a32aa7536fec09f15b51f34071a4eb86756ab5e98"
tasks:
  - id: T1
    status: done
    red: {command: "python -c \"from sparkforge_aws.portal_adapter import build_server\"", exit: 1}
    green: {command: "python -m pytest tests/test_portal_adapter.py::test_bootstrap_workspace_vazio -q", exit: 0}
  - id: T2
    status: done
    red: {command: "python -m pytest tests/test_portal_adapter.py::test_bootstrap_workspace_vazio tests/test_portal_adapter.py::test_catalogo_skills_e_agents_do_repo tests/test_portal_adapter.py::test_hosts_launch_host_ausente_recusa_nomeada tests/test_portal_adapter.py::test_install_plan_apply_verified -q", exit: 1}
    green: {command: "python -m pytest tests/test_portal_adapter.py -q", exit: 0}
  - id: T3
    status: done
    red: {command: "sparkforge-aws portal --no-browser", exit: 2}
    green: {command: "python -m pytest tests/test_portal_adapter.py::test_portal_verb_parseia -q", exit: 0}
  - id: T4
    status: done
    red: {command: "python -m pytest tests/test_portal_adapter.py::test_bootstrap_workspace_vazio tests/test_portal_adapter.py::test_catalogo_skills_e_agents_do_repo tests/test_portal_adapter.py::test_hosts_launch_host_ausente_recusa_nomeada tests/test_portal_adapter.py::test_install_plan_apply_verified -q", exit: 1}
    green: {command: "python -m pytest tests/test_portal_adapter.py -q", exit: 0}
  - id: T5
    status: done
    red: {command: "python -c \"import zipfile,glob; z=zipfile.ZipFile(glob.glob('dist/*.whl')[0]); assert any('portal_assets' in n for n in z.namelist())\"", exit: 1}
    green: {command: "python -m build --wheel", exit: 0}
claims:
  - text: "E2E em workspace scratch: NOT_INSTALLED → plan 696 ações → apply completed/PASS → VERIFIED (install-state HEALTHY + mcp-handshake PASS)."
    evidence_ref: "tests/test_portal_adapter.py::test_install_plan_apply_verified"
  - text: "MCP verify via portal: handshake real PASS, 146 tools."
    evidence_ref: "tests/test_portal_adapter.py::test_task_doctor_roundtrip"
  - text: "Catálogo real: 61 skills / 19 agents do CanonicalRegistry."
    evidence_ref: "tests/test_portal_adapter.py::test_catalogo_skills_e_agents_do_repo"
  - text: "Wheel contém 23 portal_assets + bundle skills/agents; adapter resolve os dois layouts."
    evidence_ref: "tests/test_portal_adapter.py::test_assets_index_resolvido"
  - text: "Toda mutação exige confirm + plan token; token errado → PORTAL-PLAN-STALE, intent ambíguo → SFA-PORTAL-AMBIGUOUS."
    evidence_ref: "tests/test_portal_adapter.py::test_task_intencao_ambigua_recusa_nomeada"
---

# FORGE_PORTAL — build report

## Red/green

- Red inicial observado: `api_contract` inexistente (o schema vive no
  envelope), `managed_files` vazio num install config-only, intent "doctor
  da instalação" casando `status` por ordem de needles, e `launch_command`
  presente mesmo em host `NOT_DETECTED` — todos corrigidos contra o
  comportamento real medido, não contra o esperado.
- Green: suíte `tests/test_portal_adapter.py` 17/17; gates
  `check_surface_lock.py` 0 divergências, `test_reference_docs.py` 5/5,
  `test_adapters_cli.py` 164/164, `test_docs_coverage.py` 37/37.
