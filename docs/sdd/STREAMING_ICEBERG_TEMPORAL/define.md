---
sdd: 1
feature: STREAMING_ICEBERG_TEMPORAL
phase: define
profile: dev
status: ready
upstream:
  path: docs/sdd/STREAMING_ICEBERG_TEMPORAL/explore.md
  sha256: "1a54b9c792efc82282a72b2842b3fafd96c37bd41f20c106441b3292d1aa8667"
hypothesis:
  claim: "Facts por snapshot permitem verificar se progresso Structured Streaming e commits Iceberg ocorreram na mesma janela declarada sem inferir causalidade."
  prediction: "Dumps com dois ou mais snapshots timestampados pareiam com dois ou mais batches dentro de max_skew_seconds, preservam ids e operações; dados incompletos produzem unresolved e nenhum finding temporal positivo."
  experiment: "Extrair fixtures Iceberg/progresso, compor o modo temporal Iceberg, julgar com a regra, comparar CLI/MCP e executar gates de facts, regras, fixtures, surface, documentação e runtime."
acceptance:
  - id: AC1
    statement: "O extrator emite um iceberg.snapshot por entrada válida, preservando snapshot_id, committed_at observado, operation e âncora/proveniência; timestamp inválido ou ausente permanece explicitamente não observado."
    verified_by: {kind: test, ref: tests/test_facts_iceberg_metadata.py::TestSnapshotsSummary::test_snapshot_observation_facts_preserve_identity_and_timestamp}
  - id: AC2
    statement: "A composição mode=iceberg_temporal exige table, query_name e max_skew_seconds declarados, pareia dois ou mais batches e snapshots por timestamp e preserva source_fact_ids, operações e causal_inference=false."
    verified_by: {kind: test, ref: tests/test_facts_streaming_composition.py::test_iceberg_temporal_pairs_progress_and_snapshots}
  - id: AC3
    statement: "A composição temporal emite unresolved nomeado quando falta identidade, janela, timestamp, snapshot ou segunda observação, sem transformar ausência em zero nem em causa."
    verified_by: {kind: test, ref: tests/test_facts_streaming_composition.py::test_iceberg_temporal_requires_complete_window}
  - id: AC4
    statement: "SF-STREAMICE-002 só dispara com pelo menos dois pares completos e operação não-append observada na janela, sem threshold de custo, throughput ou ganho."
    verified_by: {kind: test, ref: tests/test_streaming_rules.py::test_temporal_iceberg_rule_requires_pairs_and_non_append}
  - id: AC5
    statement: "CLI e MCP expõem mode=iceberg_temporal e max_skew_seconds pelo mesmo core e envelope, mantendo a operação read-only."
    verified_by: {kind: test, ref: tests/test_analyze_streaming_composition.py::test_iceberg_temporal_cli_and_mcp_envelopes_match}
  - id: AC6
    statement: "Goldens append, non-append temporal e unresolved cobrem os novos kinds, a regra, o ramo positivo e a regressão do modo iceberg legado."
    verified_by: {kind: test, ref: tests/test_fixtures_golden_streaming_composition.py::test_fixture_goldens}
  - id: AC7
    statement: "Knowledge, skill, mirrors, referências, prompt coverage, routing, surface lock, offline manifest e números correntes explicam a correlação temporal e seus limites."
    verified_by: {kind: command, ref: python scripts/sync_skills.py --check}
success:
  - id: SC1
    metric: "AC1–AC7 verdes; dois pares completos produzem diagnóstico temporal e operação não-append observada pode gerar finding, enquanto dados incompletos geram unresolved."
    source: "pytest focalizado, goldens, judge, CLI/MCP e gates do catálogo/surface/documentação"
out_of_scope:
  - "collector live de Spark, Iceberg, Athena, Glue ou CloudWatch"
  - "causalidade entre commit e atraso, SLO, FinOps ou ganho de throughput"
  - "inferência de timestamp por ordem de arquivo ou relógio local"
  - "replay funcional, benchmark cloud e semântica exactly-once"
unknowns:
  - id: U1
    blocks: [AC1]
    unlock: "Preservar timestamps committed_at já presentes nos dumps e emitir unresolved quando o campo não puder ser normalizado."
  - id: U2
    blocks: [AC7]
    unlock: "Regenerar goldens, referências, mirrors, surface lock e offline manifest após a mudança."
change_kinds: [extractor, fixture_corpus, knowledge_doc, tool_or_verb, rule, agent_or_skill, status_numbers]
---

# STREAMING_ICEBERG_TEMPORAL — definição

Esta feature fecha o elo observável entre progresso de uma query e histórico de
snapshots Iceberg. Ela não substitui o vínculo agregado legado; adiciona uma
janela explícita e reauditable para o caso em que o operador possui ambos os
dumps e quer saber se há operação não-append observada no mesmo intervalo.
