---
sdd: 1
feature: STREAMING_ICEBERG_TEMPORAL
phase: build_report
profile: dev
status: done
upstream:
  path: docs/sdd/STREAMING_ICEBERG_TEMPORAL/plan.md
  sha256: "d8a551048e86cb4ced1dc07ede5d4a1d194b31177034e829f98ffd1b685b1317"
tasks:
  - id: T1
    status: done
    red: {command: "python -m pytest tests/test_facts_iceberg_metadata.py::TestSnapshotsSummary::test_snapshot_observation_facts_preserve_identity_and_timestamp -q --basetemp=C:/sfpt-ice-t1-red", exit: 1}
    green: {command: "python -m pytest tests/test_facts_iceberg_metadata.py::TestSnapshotsSummary::test_snapshot_observation_facts_preserve_identity_and_timestamp -q --basetemp=C:/sfpt-ice-t1", exit: 0}
  - id: T2
    status: done
    red: {command: "python -m pytest tests/test_facts_streaming_composition.py::test_iceberg_temporal_pairs_progress_and_snapshots tests/test_facts_streaming_composition.py::test_iceberg_temporal_requires_complete_window -q --basetemp=C:/sfpt-ice-t2-red", exit: 1}
    green: {command: "python -m pytest tests/test_facts_streaming_composition.py::test_iceberg_temporal_pairs_progress_and_snapshots tests/test_facts_streaming_composition.py::test_iceberg_temporal_requires_complete_window -q --basetemp=C:/sfpt-ice-t2", exit: 0}
  - id: T3
    status: done
    red: {command: "python -m pytest tests/test_streaming_rules.py::test_temporal_iceberg_rule_requires_pairs_and_non_append -q --basetemp=C:/sfpt-ice-t3-red", exit: 1}
    green: {command: "python -m pytest tests/test_streaming_rules.py::test_temporal_iceberg_rule_requires_pairs_and_non_append -q --basetemp=C:/sfpt-ice-t3", exit: 0}
  - id: T4
    status: done
    red: {command: "python -m pytest tests/test_analyze_streaming_composition.py::test_iceberg_temporal_cli_and_mcp_envelopes_match -q --basetemp=C:/sfpt-ice-t4-red", exit: 1}
    green: {command: "python -m pytest tests/test_analyze_streaming_composition.py::test_iceberg_temporal_cli_and_mcp_envelopes_match -q --basetemp=C:/sfpt-ice-t4", exit: 0}
  - id: T5
    status: done
    red: {command: "python -m pytest tests/test_fixtures_golden_streaming_composition.py::test_fixture_goldens -q --basetemp=C:/sfpt-ice-t5-red", exit: 1}
    green: {command: "python -m pytest tests/test_fixtures_golden_streaming_composition.py::test_fixture_corpus_is_complete tests/test_fixtures_golden_streaming_composition.py::test_fixture_goldens -q --basetemp=C:/sfpt-ice-t5-green3", exit: 0}
  - id: T6
    status: done
    red: {command: "python -m pytest tests/test_reference_docs.py -q --basetemp=C:/sfpt-ice-t6", exit: 1}
    green: {command: "python -m pytest tests/test_reference_docs.py -q --basetemp=C:/sfpt-ice-t6-green", exit: 0}
claims:
  - text: "O extrator Iceberg emite um iceberg.snapshot por observação, preserva identidade, timestamp e operação observados e deixa timestamp_observed=false quando não há timestamp válido."
    evidence_ref: "tests/test_facts_iceberg_metadata.py::TestSnapshotsSummary::test_snapshot_observation_facts_preserve_identity_and_timestamp"
  - text: "O modo iceberg_temporal pareia progresso e snapshots por timestamps observados dentro da tolerância declarada, preserva source_fact_ids e causal_inference=false; janela incompleta permanece unresolved."
    evidence_ref: "tests/test_facts_streaming_composition.py::test_iceberg_temporal_pairs_progress_and_snapshots"
  - text: "SF-STREAMICE-002 exige pelo menos dois pares, janela completa e operação não-append observada, sem limiar de custo, throughput ou ganho."
    evidence_ref: "rules/catalog/streaming_iceberg.yaml; tests/test_streaming_rules.py::test_temporal_iceberg_rule_requires_pairs_and_non_append"
  - text: "CLI e MCP expõem iceberg_temporal pelo mesmo core e envelope read-only."
    evidence_ref: "tests/test_analyze_streaming_composition.py::test_iceberg_temporal_cli_and_mcp_envelopes_match"
  - text: "Goldens append, non-append, unresolved e regressão iceberg cobrem facts, diagnóstico, regra e schema de subject snapshot."
    evidence_ref: "fixtures/streaming_composition/*; tests/test_fixtures_golden_streaming_composition.py::test_fixture_goldens"
  - text: "Skill, agente, knowledge, mirrors, referências, surface lock, offline manifest, cobertura e números correntes documentam o fechamento e seus limites."
    evidence_ref: "scripts/sync_skills.py; scripts/gen_reference_docs.py; scripts/check_surface_lock.py; scripts/check_status_numbers.py --strict"
change_id: null
---

# STREAMING_ICEBERG_TEMPORAL — relatório do build

## Resultado

Build concluído em T1–T6. A feature permanece offline e determinística:
extrai observações de snapshots, compõe uma janela declarada entre progresso
Structured Streaming e commits Iceberg, e deixa causalidade, custo, SLO,
throughput, replay e semântica exactly-once fora do claim.

## Desvios e decisões durante o build

- **T5/schema.** Os novos Facts revelaram que `subject.type=snapshot` não
  estava no schema factual. O enum foi ampliado; o modo legado `iceberg`
  continua preservado e seus goldens foram regenerados.
- **T5/goldens.** O corpus ganhou `iceberg_temporal_append`,
  `iceberg_temporal_non_append` e `iceberg_temporal_unresolved`; goldens
  anteriores de Iceberg foram atualizados para incluir facts granulares.
- **T6.** A primeira rodada documental encontrou uma referência de agente
  desatualizada após a sincronização; mirrors e referências foram regenerados.
- **Ambiente.** Os testes usaram `--basetemp=C:/sfpt-ice-*` para evitar a
  permissão negada observada no diretório temporário global do Windows.
- **Escopo.** A suíte completa não foi executada nesta fase; foram executados
  testes focalizados e gates proporcionais. Nenhum ganho de custo, performance
  ou qualidade funcional é afirmado.

## Revisão por tarefa

- **T1:** snapshot_id, committed_at, operation e proveniência ficam ancorados
  por Fact; ausência ou timestamp inválido não é preenchido.
- **T2:** o pareamento usa somente timestamps timezone-aware e tolerância
  declarada; menos de dois pares ou identidade ausente emite unresolved.
- **T3:** o finding é evidence-first, preserva operações e rollback funcional,
  e mantém `causal_inference=false`.
- **T4:** CLI e MCP chamam o mesmo core; `max_skew_seconds` é explícito e a
  operação não escreve em AWS, Spark ou Iceberg.
- **T5:** fixtures positivas, negativas e incompletas cobrem o novo kind,
  regra, regressão e validação de schema.
- **T6:** skill, agente, knowledge, mirrors, referências, coverage, surface,
  manifest offline e status numbers foram atualizados.

## Medida

A medida entregue é de cobertura e contrato: observações granulares, pares
temporais determinísticos, evidência ancorada e recusa nomeada. Não há medição
de throughput, latência, custo, capacidade ou resultado funcional.
