---
sdd: 1
feature: SDD_MIGRATION
phase: design
profile: dev
status: ready
upstream:
  path: docs/sdd/SDD_MIGRATION/define.md
  sha256: "3f1b1f3d9e4c78a26d2dc0414c54e2098660ff5848277bb6879cc4612185b25f"
files:
  - {path: .claude/settings.json, action: modify, reason: "agentspec@agentspec false em enabledPlugins"}
  - {path: .claude/sdd, action: delete, reason: "git mv para docs/sdd/archive/agentspec/; .detected-stack.md sai por git rm"}
  - {path: .gitignore, action: modify, reason: ".claude/sdd/ e .sparkforge/journal.jsonl ignorados neste repositorio"}
  - {path: docs/sdd/archive/agentspec, action: create, reason: "destino do historico, conteudo identico"}
  - {path: docs/superpowers/README.md, action: create, reason: "specs/ e plans/ congelados; STATUS.md continua vivo"}
  - {path: CLAUDE.md, action: modify, reason: "secao curta: spec e desenvolvimento pelo SDD proprio"}
  - {path: AGENTS.md, action: modify, reason: "mesma instrucao para os outros agentes"}
  - {path: CONTRIBUTING.md, action: modify, reason: "fluxo de mudanca grande aponta docs/sdd e as skills"}
  - {path: README.md, action: modify, reason: "secao do SDD proprio"}
  - {path: tests/test_sdd_migration.py, action: create, reason: "AC1 a AC5"}
decisions:
  - id: D1
    choice: "Arquivar por git mv, sem editar os documentos antigos."
    rejected: ["converter os 104 documentos do AgentSpec para o formato novo", "apagar o historico"]
    rollback: "git mv docs/sdd/archive/agentspec de volta para .claude/sdd e remover a linha do .gitignore."
  - id: D2
    choice: "docs/superpowers/ fica onde esta; so ganha um README de congelamento."
    rejected: ["mover docs/superpowers, o que quebraria dezenas de referencias, inclusive CLAUDE.md, AGENTS.md e docs auditados pelo gate de lastro"]
    rollback: "Apagar docs/superpowers/README.md."
  - id: D3
    choice: "Desligar o AgentSpec so no projeto, em .claude/settings.json."
    rejected: ["editar a configuracao de usuario do operador, que nao e do repositorio"]
    rollback: "Remover a chave agentspec@agentspec de enabledPlugins."
covers:
  - {part: "settings", acceptance: [AC1]}
  - {part: "arquivo", acceptance: [AC2, AC3]}
  - {part: "documentos de entrada", acceptance: [AC4, AC5]}
---

# SDD_MIGRATION — desenho

## Riscos conferidos antes

- `tests/test_agents_parity.py::TestNoPlatformKnowledge` le todo `.md` sob
  `.claude/`; tirar `.claude/sdd/` de la remove uma armadilha conhecida.
- `docs/sdd/archive/agentspec/` fica fundo demais e com nome minusculo:
  `discover` nao o toma por feature.
- `CLAUDE.md` tem teto em `tests/test_bootstrap_budget.py`: a secao nova e curta
  e aponta para `docs/sdd/README.md`.
- `.claude/agents/README.md` nao rastreado e scaffolding do AgentSpec; com o
  plugin desligado ele para de reaparecer. Nao e apagado por este trabalho.
