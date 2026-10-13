---
sdd: 1
feature: AGENTIC_ENGINEERING_OS_V2
phase: define
profile: dev
status: ready
upstream:
  path: docs/sdd/AGENTIC_ENGINEERING_OS_V2/explore.md
  sha256: "571bbf0e880d92a62f39efa9072498a73491207e800ce809aea77abb5c7c9976"
hypothesis:
  claim: "Contratos determinísticos e opt-in para memória, trust, contexto, economia, routing, AgentOps e interoperabilidade tornam evolução agentic mais auditável e econômica sem quebrar a superfície legada."
  prediction: "Os novos contratos bloquearão memória sem evidência/outcome, preservarão dados externos como não-instrução, calcularão métricas sem converter bytes em tokens, manterão routing shadow fail-closed e permitirão comparar runs locais; CLI e MCP devolverão o mesmo envelope."
  experiment: "Executar a suíte final contra testes de contratos, chamar os novos verbos com fixtures locais, verificar paridade CLI/MCP e rodar os gates de superfície, referências, claims e SDD."
acceptance:
  - id: AC1
    statement: "DecisionMemoryRecord, MemoryCandidate e trust gate persistem somente decisões com evidência válida, isolam case e permitem quarantine, outcome, freshness, invalidation e supersession."
    verified_by: {kind: test, ref: "tests/test_agentic_os_v2.py::test_memory_trust_gate_and_retrieval"}
    guard: "Execução de testes foi deliberadamente adiada para a suíte final por instrução do operador."
  - id: AC2
    statement: "TrustEnvelope e RoleContextPlan carregam origin, trust, scope, instruction_authority, taint, provenance e freshness; conteúdo externo e handoff não ganham autoridade de instrução."
    verified_by: {kind: test, ref: "tests/test_agentic_os_v2.py::test_trust_and_role_context_isolation"}
    guard: "Execução de testes foi deliberadamente adiada para a suíte final por instrução do operador."
  - id: AC3
    statement: "ContextQualityReport calcula recall, precision, density, duplicação, stale, expansão, reuse, cache hit e evidence-per-token com bytes separados de tokens observados, e compara níveis A/B/C."
    verified_by: {kind: test, ref: "tests/test_agentic_os_v2.py::test_context_quality_and_minimum_sufficient_context"}
    guard: "Execução de testes foi deliberadamente adiada para a suíte final por instrução do operador."
  - id: AC4
    statement: "TokenLedger unifica eventos de host/tool/agent/case/provider, reconcilia estimated versus observed e recusa custo sem cost_basis ou provider transcript."
    verified_by: {kind: test, ref: "tests/test_agentic_os_v2.py::test_token_ledger_reconciliation_is_explicit"}
    guard: "Execução de testes foi deliberadamente adiada para a suíte final por instrução do operador."
  - id: AC5
    statement: "AdaptiveModelRouter registra scorecard, decide por complexidade/risco/contexto/tool support/quality/cost/latency/budget e permanece shadow por default, sem confundir case routing."
    verified_by: {kind: test, ref: "tests/test_agentic_os_v2.py::test_model_router_is_shadow_by_default"}
    guard: "Execução de testes foi deliberadamente adiada para a suíte final por instrução do operador."
  - id: AC6
    statement: "AgentOps inspeciona e compara traces locais, cria baseline/regression findings e classifica waste como observed, estimated ou hypothesis."
    verified_by: {kind: test, ref: "tests/test_agentic_os_v2.py::test_agentops_inspect_compare_baseline"}
    guard: "Execução de testes foi deliberadamente adiada para a suíte final por instrução do operador."
  - id: AC7
    statement: "SemanticCheckpoint e Forge protocol publicam estado resumível e envelopes ForgeCapability, ForgeTask, ForgeEvidenceBundle, ForgeHandoff, ForgeResult e ForgeHealth sem expor detalhes internos."
    verified_by: {kind: test, ref: "tests/test_agentic_os_v2.py::test_checkpoint_and_forge_protocol_are_content_addressed"}
    guard: "Execução de testes foi deliberadamente adiada para a suíte final por instrução do operador."
  - id: AC8
    statement: "CLI e MCP expõem context inspect, agentops inspect/compare/baseline e doctor agentic com schemas estruturados, mantendo ferramentas existentes e local-first."
    verified_by: {kind: test, ref: "tests/test_agentic_os_v2.py::test_cli_mcp_and_doctor_surfaces"}
    guard: "Execução de testes foi deliberadamente adiada para a suíte final por instrução do operador."
success:
  - id: SC1
    metric: "Suíte final e testes de contrato AC1–AC8 passam"
    source: "python -m pytest -q -p no:randomly"
  - id: SC2
    metric: "CLI/MCP devolvem envelopes equivalentes para as novas operações"
    source: "tests/test_agentic_os_v2.py::test_cli_mcp_and_doctor_surfaces"
  - id: SC3
    metric: "Nenhuma afirmação de provider tokens, custo ou ganho fica sem transcript/cost_basis/benchmark"
    source: "tests/test_agentic_os_v2.py::test_token_ledger_reconciliation_is_explicit"
out_of_scope:
  - "Live-model eval e preço atual de providers sem transcript e fonte efetiva."
  - "Ativação active, escrita automática de memória institucional e execução AWS."
  - "Vector database obrigatório ou dependência nova de provider."
  - "Reescrita do Context Gateway, Decision Plane, traces SQLite ou MCP server legados."
unknowns:
  - id: U1
    blocks: [SC1]
    unlock: "Rodar suíte final e registrar resultado reproduzível; nenhum teste deve ser executado antes desta etapa por restrição do operador."
  - id: U2
    blocks: [SC3]
    unlock: "Fornecer transcript do host e tabela de preço com effective_date; até lá provider_tokens e dólares ficam unresolved."
case_id: null
change_kinds: [disk_read, tool_or_verb, claims]
---

# AGENTIC_ENGINEERING_OS_V2 — requisitos

Entrega vertical dos gaps auditados. O design deve cobrir cada AC e preservar
compatibilidade de imports, CLI, MCP, JSONL de memória e SQLite de traces.
