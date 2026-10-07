---
sdd: 1
feature: STREAMING_INTEGRATIONS_AND_CHECKPOINTS
phase: define
profile: dev
status: ready
upstream:
  path: docs/sdd/STREAMING_INTEGRATIONS_AND_CHECKPOINTS/explore.md
  sha256: "95d2644f9e963f53b4d237f0306945220009259a69ef092df78f54186ed77b21"
hypothesis:
  claim: "Um contrato offline tipado torna lacunas de checkpoint, Connect, Streams e OpenLineage julgáveis sem inventar saúde ou lineage."
  prediction: "Artefatos completos produzem facts; campos ausentes produzem unresolved e regras P1; secrets não persistem."
  experiment: "Executar goldens completo/incompleto, comparar CLI/MCP, julgar regras e rodar surface/offline/SDD gates."
acceptance:
  - id: AC1
    statement: "Checkpoint preserva identidade e séries declaradas, recusando tendência com uma amostra."
    verified_by: {kind: test, ref: tests/test_streaming_integrations.py::test_goldens_cover_checkpoint_connect_streams_and_openlineage}
  - id: AC2
    statement: "Kafka Connect preserva connector/tasks/status/offsets sanitizados e nomeia contexto ausente."
    verified_by: {kind: test, ref: tests/test_streaming_integrations.py::test_goldens_cover_checkpoint_connect_streams_and_openlineage}
  - id: AC3
    statement: "Kafka Streams preserva topology/state stores/changelog/repartition e não afirma candidato melhor sozinho."
    verified_by: {kind: test, ref: tests/test_streaming_integrations.py::test_goldens_cover_checkpoint_connect_streams_and_openlineage}
  - id: AC4
    statement: "OpenLineage preserva Job/Run/datasets/facets declarados e emite unresolved quando a identidade falta."
    verified_by: {kind: test, ref: tests/test_streaming_integrations.py::test_goldens_cover_checkpoint_connect_streams_and_openlineage}
  - id: AC5
    statement: "CLI e MCP retornam o mesmo envelope determinístico."
    verified_by: {kind: test, ref: tests/test_streaming_integrations.py::test_cli_and_mcp_envelopes_match}
  - id: AC6
    statement: "Rules, knowledge, fixtures, references, manifest, mirrors e gates permanecem coerentes."
    verified_by: {kind: command, ref: python scripts/check_surface_lock.py}
success:
  - id: SC1
    metric: "AC1–AC6 verdes; coleta live e eficácia runtime permanecem unresolved sem artefato."
    source: "pytest focado e gates offline"
out_of_scope:
  - "conectar ao Kafka Connect REST, broker, MSK ou OpenLineage"
  - "replay, benchmark temporal e validação funcional de delivery"
  - "copiar secrets, calcular custo ou declarar exactly-once end-to-end"
unknowns:
  - id: U1
    blocks: [AC6]
    unlock: "Regenerar surface, fontes, offline manifest, referências, contagens e mirrors."
  - id: U2
    blocks: []
    unlock: "Endpoint/credencial/janela operacional para collector live; fora desta wave por offline guarantee."
change_kinds: [extractor, fixture_corpus, knowledge_doc, tool_or_verb, rule, status_numbers]
---

# STREAMING_INTEGRATIONS_AND_CHECKPOINTS — definição

O resultado é diagnóstico de artefato salvo, com blind spots explícitos.
