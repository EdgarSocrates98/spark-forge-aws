---
sdd: 1
feature: STREAMING_END_TO_END_PIPELINE
phase: define
profile: dev
status: ready
upstream:
  path: docs/sdd/STREAMING_END_TO_END_PIPELINE/explore.md
  sha256: "79683f70f15f1d32e88ba5d4f53ddf4464bc1af57fa5a66e29b18f934673382c"
hypothesis:
  claim: "Um modo pipeline declarativo no compositor existente permite verificar arestas end-to-end somente quando selectors explícitos encontram facts sem ambiguidade, mantendo blind spots nomeados e payload compacto."
  prediction: "Um contrato válido com selectors únicos produz nodes observados, edges verified e fact streaming.pipeline; selector ausente, duplicado ou contrato inválido produz streaming.pipeline.unresolved; nenhum vínculo é inferido por ordem, nome parcial ou coexistência de artifacts; CLI e MCP permanecem equivalentes."
  experiment: "Adicionar testes vermelhos para contrato/seleção/composição e paridade, implementar o modo, criar goldens de pipeline completo/incompleto/ambíguo e executar gates focados de regras, fixtures, surface, docs e SDD."
acceptance:
  - id: AC1
    statement: "O compositor aceita contrato pipeline versionado com nodes e edges, rejeita shape inválido por unresolved nomeado e preserva input_fact_ids/provenance."
    verified_by: {kind: test, ref: "tests/test_streaming_pipeline.py::test_pipeline_contract_emits_verified_nodes_and_edges"}
  - id: AC2
    statement: "Selectors exigem kind e atributos escalares declarados; zero matches, múltiplos matches e edge com endpoint não observado produzem streaming.pipeline.unresolved sem vínculo inventado."
    verified_by: {kind: test, ref: "tests/test_streaming_pipeline.py::test_pipeline_missing_and_ambiguous_selectors_stay_unresolved"}
  - id: AC3
    statement: "A regra SF-STREAM-015 julga somente pipeline.unresolved observado e exige evidência do blind spot; pipeline completo não dispara finding."
    verified_by: {kind: test, ref: "tests/test_streaming_pipeline.py::test_pipeline_rule_fires_only_for_observed_blind_spot"}
  - id: AC4
    statement: "O modo pipeline mantém paridade entre core/CLI/MCP e paginação detail_level do compositor existente."
    verified_by: {kind: test, ref: "tests/test_streaming_pipeline.py::test_pipeline_cli_mcp_envelopes_match"}
  - id: AC5
    statement: "Goldens cobrem pipeline completo, selector ausente, selector ambíguo e contrato inválido com facts/finding determinísticos."
    verified_by: {kind: test, ref: "tests/test_fixtures_golden_streaming_pipeline.py::test_streaming_pipeline_fixture_corpus_is_complete"}
  - id: AC6
    statement: "Knowledge, skill, coordenador, guias, referências geradas, surface lock e números correntes documentam o modo e seus limites sem claim de latência, throughput, causa, saúde ou custo."
    verified_by: {kind: command, ref: "python scripts/check_status_numbers.py --strict"}
success:
  - id: SC1
    metric: "AC1–AC6 verdes; cada edge verified carrega source_fact_ids e cada blind spot permanece unresolved."
    source: "pytest focado de pipeline/rules/goldens e gates de catálogo, superfície, docs e status"
out_of_scope:
  - "Descoberta automática de topologia, matching por substring, ordem de arquivo ou nome de serviço."
  - "Collector live, execução/replay, latência, throughput, custo, saúde, SLO, causalidade ou exatamente-once end-to-end."
  - "Mutação de broker, runtime, schema registry, sink ou qualquer provider."
unknowns:
  - id: U1
    blocks: [AC1, AC2]
    unlock: "Contrato real com selectors versionados e facts sanitizados de cada etapa do pipeline."
  - id: U2
    blocks: [AC6]
    unlock: "Regenerar locks e referências após a nova modalidade e documentar os limites no mapa de streaming."
case_id: null
change_kinds: [extractor, disk_read, rule, rule_runtime_scope, fixture_corpus, knowledge_doc, agent_or_skill, tool_or_verb, status_numbers]
---

# STREAMING_END_TO_END_PIPELINE — requisitos

Esta feature compõe topologia declarada com evidência observada. O contrato não
transforma uma sequência de arquivos em pipeline; cada vínculo precisa de
identidade explícita e fato correspondente.
