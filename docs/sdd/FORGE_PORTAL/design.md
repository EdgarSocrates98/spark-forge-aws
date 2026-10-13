---
sdd: 1
feature: FORGE_PORTAL
phase: design
profile: dev
status: ready
upstream:
  path: docs/sdd/FORGE_PORTAL/define.md
  sha256: "fb51a6af15ef441cf1bee9474d5ce0167a23c07deb5aa7fa4ac5c485bd7ff1f9"
files:
  - {path: "sparkforge_aws/_forge_portal.py", action: "create", reason: "servidor stdlib canônico vendored do forge-portal (byte-identical, linted lá)"}
  - {path: "sparkforge_aws/portal_adapter.py", action: "create", reason: "adapter forge/PortalApi/1 → lifecycle/open_host/registry/graphview"}
  - {path: "sparkforge_aws/adapters/cli.py", action: "modify", reason: "verbo `portal` + dispatch com --no-browser/--port/--root"}
  - {path: "portal/assets/", action: "create", reason: "SPA Angular vendored + manifest sha256"}
  - {path: "tests/test_portal_adapter.py", action: "create", reason: "15 testes do contrato HTTP real"}
  - {path: "pyproject.toml", action: "modify", reason: "force-include portal/assets → sparkforge_aws/portal_assets no wheel"}
  - {path: "docs/reference/command-rationale.json", action: "modify", reason: "rationale do verbo portal"}
  - {path: "docs/learn/recipes/portal.md", action: "create", reason: "receita portal (o quê/por que/quando)"}
decisions:
  - id: D1
    choice: "Adapter importa serviços do pacote — nunca subprocess/CLI nem reimplementação."
    rollback: "Apagar portal_adapter.py e o verbo portal do dispatch; nenhum serviço existente muda."
  - id: D2
    choice: "Catálogo skills/agents resolve _REPO_ROOT (clone) com fallback integrate/bundle (wheel); workspace do usuário nunca é catálogo."
    rollback: "Voltar _registry() a CanonicalRegistry(workspace); catálogo volta a depender do cwd."
  - id: D3
    choice: "Mutação passa por plan→token→confirm→receipt; o plano ecoado é a fonte da verdade verificada pelo HMAC."
    rollback: "Aceitar apply/execute sem eco do plano reabre adulteração — desfazer é restaurar check_plan no corpo."
  - id: D4
    choice: "hosts/launch devolve o comando a copiar — o portal não tem TTY e nunca executa cego."
    rollback: "Lançar o host pelo portal exigiria subprocess cego; o recuo é rejeitar launch sem TTY."
  - id: D5
    choice: "Tasks mapeiam intent a verbos read-only conhecidos; ambíguo → SFA-PORTAL-AMBIGUOUS com safe_verbs."
    rollback: "Ampliar o mapa de intents; remover o fallthrough de recusa reabre execução adivinhada."
covers:
  - {part: "verbo portal no dispatch do cli.py", acceptance: ["AC1"]}
  - {part: "health() mapeia healthy/degraded/unverified/broken para o enum do portal", acceptance: ["AC2"]}
  - {part: "_registry() com candidatos clone/bundle do wheel", acceptance: ["AC3"]}
  - {part: "ops com confirm= e needs_plan_token no servidor vendored", acceptance: ["AC4", "AC6"]}
  - {part: "_ASSETS_CANDIDATES + force-include no wheel", acceptance: ["AC5"]}
---

# FORGE_PORTAL — desenho

## Notas

- `install 'all'` pode ser recusado de verdade (`.mcp.json` existente →
  `sparkforge_aws_ja_configurado`): o receipt com `refused[]` é o produto,
  o portal o devolve intacto.
- Vocabulário real: lifecycle emite `healthy|degraded|unverified|broken`,
  open_host emite `NOT_DETECTED|DETECTED|SUPPORTED|READY|NEEDS_LOGIN|
  INTEGRATION_*` — os mapeamentos usam os estados reais, não suposições.
