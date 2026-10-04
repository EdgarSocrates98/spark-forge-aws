---
sdd: 1
feature: AGENTIC_ENGINEERING_OS_V2
phase: plan
profile: dev
status: ready
upstream:
  path: docs/sdd/AGENTIC_ENGINEERING_OS_V2/design.md
  sha256: "80a6b89c5c312afda720e2159722441faba9451f0ff2c9ec53c5a14968ef3d8e"
tasks:
  - {id: T1, files: [tests/test_agentic_os_v2.py, sparkforge/agentic/trust.py, sparkforge/agentic/memory.py], covers: [AC1, AC2], test: {path: tests/test_agentic_os_v2.py, name: test_memory_trust_gate_and_retrieval}}
  - {id: T2, files: [tests/test_agentic_os_v2.py, sparkforge/context/quality.py, sparkforge/agentic/checkpoint.py, sparkforge/protocols/forge.py, sparkforge/protocols/__init__.py], covers: [AC3, AC7], test: {path: tests/test_agentic_os_v2.py, name: test_context_quality_and_minimum_sufficient_context}}
  - {id: T3, files: [tests/test_agentic_os_v2.py, sparkforge/economy/ledger.py, sparkforge/economy/model_router.py], covers: [AC4, AC5], test: {path: tests/test_agentic_os_v2.py, name: test_token_ledger_reconciliation_is_explicit}}
  - {id: T4, files: [tests/test_agentic_os_v2.py, sparkforge/observability/agentops.py], covers: [AC6], test: {path: tests/test_agentic_os_v2.py, name: test_agentops_inspect_compare_baseline}}
  - {id: T5, files: [tests/test_agentic_os_v2.py, sparkforge/adapters/_core.py, sparkforge/adapters/cli.py, sparkforge/adapters/tools.py, sparkforge/agentic/__init__.py], covers: [AC8], test: {path: tests/test_agentic_os_v2.py, name: test_cli_mcp_and_doctor_surfaces}}
  - {id: T6, files: [README.md, GUIA_DE_USO.md, docs/vnext/ARCHITECTURE.md, docs/vnext/CURRENT-STATE.md, docs/vnext/FINAL-REPORT.md, docs/vnext/adrs/ADR-012-agentic-os-v2-contracts.md], covers: [AC8], test: {path: tests/test_agentic_os_v2.py, name: test_documentation_describes_evidence_limits}}
---

# AGENTIC_ENGINEERING_OS_V2 — plano

## T1 — memória, trust e handoff

Escrever `tests/test_agentic_os_v2.py` primeiro com casos de evidência válida,
quarantine, outcome ranking, incompatibilidade de runtime, trust/taint e
requested action não-instrucional. Implementar `trust.py`; estender
`memory.py` por funções compatíveis (`record_decision`, `update_outcome`,
`find_similar_decisions`) e adicionar `DecisionMemoryRecord`, candidate gate,
fingerprints, invalidation e retrieval exact/lexical/environment/runtime/graph
sem embedding obrigatório. Commit `feat(agentic): gate institutional memory and trust envelopes`.

## T2 — qualidade de contexto, checkpoint e protocolo Forge

Implementar métricas puras em `context/quality.py`, benchmark A/B/C com ponto de
parada explícito, checkpoint semântico content-addressed e contratos públicos
Forge serializáveis. Nenhuma métrica converte bytes em tokens sem valor
observado. Commit `feat(agentic): add context quality checkpoints and forge contracts`.

## T3 — ledger e model router

Implementar eventos de ledger, reconciliação estimado/observado, perfis de preço
com `effective_date` e router independente com scorecard, shadow default e
promotion evidence. Reusar `ExecutionProfile`/`RiskLevel` sem alterar
`CapabilityModelRouter`. Commit `feat(economy): unify token ledger and gated model routing`.

## T4 — AgentOps

Implementar leitura read-only dos traces SQLite/JSON serializados, inspect,
compare, baseline e findings de waste com classificação de origem. Commit
`feat(observability): add local agentops inspection and regression baselines`.

## T5 — adapters

Adicionar funções `_core` e handlers/declarações CLI/MCP para `context inspect`,
`agentops inspect|compare|baseline` e `doctor agentic`. Schemas devem expor
summary/refs/items/unresolved/pagination/evidence quando aplicável. Atualizar
exports. Commit `feat(adapters): expose agentic os inspection surfaces`.

## T6 — documentação e gates

Atualizar README, guia, arquitetura, estado, relatório e ADR com capacidades
observadas, limites e gaps unresolved; não publicar números inventados. Rodar
gates de geração/superfície/claims/referências antes da suíte final. Commit
`docs(agentic): document v2 contracts and evidence boundaries`.
