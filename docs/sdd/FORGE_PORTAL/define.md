---
sdd: 1
feature: FORGE_PORTAL
phase: define
profile: dev
status: ready
upstream:
  path: docs/sdd/FORGE_PORTAL/explore.md
  sha256: "993bb6603b59ac17940936bf952d73ef5b8048cd541a3ad9b0cf803a68b747bb"
hypothesis:
  claim: "Uma UI web local sobre os serviços reais do pacote torna a forja utilizável por quem não aprende por CLI, sem fabricar estado nem duplicar o motor."
  prediction: "O verbo `portal` serve bootstrap/health/hosts/mcp/skills/agents/docs com dados reais; a jornada instalar→verificar→primeira tarefa fecha num workspace vazio com receipts idênticos ao CLI."
  experiment: "Subir o servidor num tmp_path e exercer bootstrap, plan/apply com plan token, mcp verify, tasks e docs search via HTTP; medir também o wheel force-included."
acceptance:
  - id: AC1
    statement: "`sparkforge-aws portal` sobe o servidor stdlib vendored e imprime a URL com token de sessão."
    verified_by: {kind: command, ref: "sparkforge-aws portal --no-browser"}
  - id: AC2
    statement: "Bootstrap/health refletem o lifecycle real: NOT_INSTALLED sem ledger, VERIFIED após install com handshake MCP PASS."
    verified_by: {kind: test, ref: "tests/test_portal_adapter.py::test_install_plan_apply_verified"}
  - id: AC3
    statement: "Skills e agents vêm do CanonicalRegistry do pacote (clone ou bundle do wheel), nunca do workspace do usuário."
    verified_by: {kind: test, ref: "tests/test_portal_adapter.py::test_catalogo_skills_e_agents_do_repo"}
  - id: AC4
    statement: "Toda mutação exige confirm + plan token assinado: token errado devolve PORTAL-PLAN-STALE, sem confirm devolve PORTAL-CONFIRM."
    verified_by: {kind: test, ref: "tests/test_portal_adapter.py::test_install_plan_apply_verified"}
  - id: AC5
    statement: "O wheel carrega portal_assets e o adapter resolve assets/catálogo nos dois layouts (clone e pip install)."
    verified_by: {kind: command, ref: "python -m build --wheel"}
  - id: AC6
    statement: "Intent fora do conjunto seguro devolve SFA-PORTAL-AMBIGUOUS com safe_verbs — o ramo default do roteador determinístico, nunca um chute."
    verified_by: {kind: test, ref: "tests/test_portal_adapter.py::test_task_intencao_ambigua_recusa_nomeada"}
    guard: "a recusa e o fallthrough por construcao do roteador (D5): todo intent sem needle casado devolve SFA-PORTAL-AMBIGUOUS desde a primeira versao; o teste e guarda de regressao desse ramo"
success:
  - id: SC1
    metric: "Endpoints reais respondendo no servidor vendored"
    source: "saída HTTP de /api/v1/* no E2E"
  - id: SC2
    metric: "Receipts forge/* idênticos aos do CLI"
    source: ".sparkforge_aws/receipts/ no workspace do portal"
out_of_scope:
  - "Servir o portal fora de 127.0.0.1 ou sem token de sessão."
  - "Lançar o host de IA de dentro do portal (sem TTY — o verbo devolve o comando)."
  - "Federar outras forjas (FASE 7 do forge-portal)."
change_kinds: [tool_or_verb, disk_read, dependency]
---

# FORGE_PORTAL — definição

## Hipótese

Portal real = superfície sobre serviços existentes. Qualquer estado que o CLI
não consegue provar fica `unverified`; qualquer intent fora do conjunto
seguro de tasks vira recusa nomeada com a lista do que existe.
