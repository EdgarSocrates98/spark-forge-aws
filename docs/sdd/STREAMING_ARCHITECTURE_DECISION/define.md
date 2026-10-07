---
sdd: 1
feature: STREAMING_ARCHITECTURE_DECISION
phase: define
profile: dev
status: ready
upstream:
  path: docs/sdd/STREAMING_ARCHITECTURE_DECISION/explore.md
  sha256: "7fcbed1bb4bb570fd70e6c9ecbc234d0033866aae75b75af3d4a5e7398bb1e7f"
hypothesis:
  claim: "Uma matriz determinística que separa requirements de assumptions reduz decisões arquiteturais não auditáveis."
  prediction: "Empate gera ADR unresolved; constraints fortes podem selecionar um candidato; assumption nunca elimina."
  experiment: "Rodar fixtures ambiguous, unique e insufficient, CLI, skill mirrors, references e gates."
acceptance:
  - id: AC1
    statement: "Requirements e assumptions aparecem em campos separados e facts de requisito têm ids estáveis."
    verified_by: {kind: test, ref: tests/test_streaming_architecture.py::test_fixture_results_are_stable_and_requirements_stay_separate}
  - id: AC2
    statement: "Mais de um candidato suportado mantém decisão e ADR unresolved, sem vencedor artificial."
    verified_by: {kind: test, ref: tests/test_streaming_architecture.py::test_candidate_matrix_refuses_underdetermined_winner}
  - id: AC3
    statement: "Constraints factuais deixam Glue Streaming como único candidato no cenário managed Spark declarado."
    verified_by: {kind: test, ref: tests/test_streaming_architecture.py::test_hard_constraints_can_leave_one_candidate_without_soft_ranking}
  - id: AC4
    statement: "CLI persiste e imprime o mesmo ADR/matriz, sem abrir superfície MCP nova."
    verified_by: {kind: test, ref: tests/test_streaming_architecture.py::test_cli_emits_adr_and_matrix}
  - id: AC5
    statement: "Knowledge, skill, mirrors, referências e status permanecem sincronizados."
    verified_by: {kind: command, ref: python scripts/sync_skills.py --check}
success:
  - id: SC1
    metric: "AC1–AC5 verdes; ausência de benchmark/custo/SLO permanece unresolved."
    source: "pytest do engine/fixtures/CLI e gates de integração"
out_of_scope:
  - "collector de runtime ou capacidade"
  - "benchmark, preço ou vencedor por custo"
  - "integração automática com facts de execução"
  - "provisionamento ou alteração live"
unknowns:
  - id: U1
    blocks: [AC3]
    unlock: "Capturar runtime, versão, capacidade e restrições do ambiente alvo."
  - id: U2
    blocks: [AC4]
    unlock: "Integrar facts de serving, SLO, segurança e custo em composição posterior."
change_kinds: [tool_or_verb, fixture_corpus, knowledge_doc, agent_or_skill, status_numbers]
---

# STREAMING_ARCHITECTURE_DECISION — definição

O motor faz eliminação factual, não otimização multiobjetivo. A decisão
continua reabrível quando novos facts substituírem assumptions.
