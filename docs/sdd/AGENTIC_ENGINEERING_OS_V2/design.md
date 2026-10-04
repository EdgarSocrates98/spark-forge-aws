---
sdd: 1
feature: AGENTIC_ENGINEERING_OS_V2
phase: design
profile: dev
status: ready
upstream:
  path: docs/sdd/AGENTIC_ENGINEERING_OS_V2/define.md
  sha256: "4e4736f8176ece72557320661119f25e38811e1eeaf26f936f07c331a36f97cc"
files:
  - {path: tests/test_agentic_os_v2.py, action: create, reason: "contratos AC1-AC8 e paridade das superfícies"}
  - {path: sparkforge/agentic/trust.py, action: create, reason: "TrustEnvelope, RoleContextPlan, sanitização e autoridade"}
  - {path: sparkforge/agentic/memory.py, action: modify, reason: "DecisionMemoryRecord, candidate gate, retrieval híbrido e invalidação compatível"}
  - {path: sparkforge/agentic/checkpoint.py, action: create, reason: "checkpoint semântico resumível e content-addressed"}
  - {path: sparkforge/protocols/forge.py, action: create, reason: "contratos mínimos de interoperabilidade Forge/A2A"}
  - {path: sparkforge/protocols/__init__.py, action: create, reason: "export público dos contratos Forge"}
  - {path: sparkforge/context/quality.py, action: create, reason: "métricas de qualidade e minimum sufficient context"}
  - {path: sparkforge/economy/ledger.py, action: create, reason: "ledger unificado e reconciliação sem inferir tokens/custo"}
  - {path: sparkforge/economy/model_router.py, action: create, reason: "router independente com scorecard e modos gated"}
  - {path: sparkforge/observability/agentops.py, action: create, reason: "inspect/compare/baseline e waste attribution"}
  - {path: sparkforge/adapters/_core.py, action: modify, reason: "funções compartilhadas CLI/MCP para superfícies novas"}
  - {path: sparkforge/adapters/cli.py, action: modify, reason: "verbos context inspect, agentops e doctor agentic"}
  - {path: sparkforge/adapters/tools.py, action: modify, reason: "tools MCP equivalentes aos verbos novos"}
  - {path: sparkforge/agentic/__init__.py, action: modify, reason: "exports dos contratos agentic novos"}
  - {path: README.md, action: modify, reason: "descrição de capabilities e comandos novos"}
  - {path: GUIA_DE_USO.md, action: modify, reason: "uso operacional local-first e limites de evidência"}
  - {path: docs/vnext/ARCHITECTURE.md, action: modify, reason: "arquitetura after alinhada com produção"}
  - {path: docs/vnext/CURRENT-STATE.md, action: modify, reason: "inventário e gaps reancorados em código"}
  - {path: docs/vnext/FINAL-REPORT.md, action: modify, reason: "relatório sem claims quantitativos sem lastro"}
  - {path: docs/vnext/adrs/ADR-012-agentic-os-v2-contracts.md, action: create, reason: "boundary e rollback da evolução"}
decisions:
  - id: D1
    choice: "Adicionar contratos puros e adaptadores, mantendo módulos legados e active routing disabled."
    rejected: ["reescrita do kernel, por risco de regressão e impossível atribuição de causa", "vector DB obrigatório, por quebrar local-first e economia"]
    rollback: "git revert dos commits da onda; APIs legadas continuam no commit anterior e arquivos novos deixam de ser importados."
  - id: D2
    choice: "Trust e instruction_authority são propriedades distintas; dados externos podem virar fact por extractor, mas nunca instrução."
    rejected: ["booleano trusted/untrusted único, por perder origem, taint e escopo", "sanitização por remoção de texto, por destruir evidência"]
    rollback: "git revert da onda de trust e voltar ao guardrail marker-only existente."
  - id: D3
    choice: "Tokens observados só vêm de transcript; bytes permanecem bytes; custo exige cost_basis e data."
    rejected: ["converter bytes por divisor fixo, proibido pelas regras de economia", "hardcode de preço, por envelhecimento silencioso"]
    rollback: "git revert da onda de ledger; ContextLedger existente continua medindo payload_bytes."
  - id: D4
    choice: "CLI e MCP usam as mesmas funções do _core e schemas compactos; superfícies novas são read-only."
    rejected: ["CLI-only, por quebrar parity", "expor objetos internos completos, por aumentar payload e acoplamento"]
    rollback: "git revert dos adaptadores e manter bibliotecas novas disponíveis sem surface pública."
covers:
  - {part: "memory trust and retrieval", acceptance: [AC1]}
  - {part: "trust and role context", acceptance: [AC2]}
  - {part: "context quality", acceptance: [AC3]}
  - {part: "token ledger", acceptance: [AC4]}
  - {part: "model routing", acceptance: [AC5]}
  - {part: "agentops", acceptance: [AC6]}
  - {part: "checkpoint and Forge protocol", acceptance: [AC7]}
  - {part: "adapters and docs", acceptance: [AC8]}
---

# AGENTIC_ENGINEERING_OS_V2 — desenho

Todas as implementações são offline-first, serializáveis e sem import de SDK de
provider. JSONL de memória ganha campos novos preservando records antigos como
`legacy_untrusted`; SQLite de traces não muda schema nesta onda. Claims de
desempenho, custo e qualidade só aparecem como métricas reproduzíveis ou
`unresolved`.

## Conhecimento consultado

- `sparkforge sdd status --repo .`, `sparkforge agents list --repo .` e
  `sparkforge playbook ...` para inventário e roteamento.
- `docs/vnext/CURRENT-STATE.md`, `docs/vnext/ARCHITECTURE.md`,
  `sparkforge/agentic/memory.py`, `sparkforge/agentic/security.py`,
  `sparkforge/context/`, `sparkforge/economy/`, `sparkforge/observability/`.
- `sparkforge/sdd/change_kinds.yaml` e `docs/gates-por-mudanca.md` para gates.
