---
sdd: 1
feature: STREAMING_END_TO_END_PIPELINE
phase: build_report
profile: dev
status: done
upstream:
  path: docs/sdd/STREAMING_END_TO_END_PIPELINE/plan.md
  sha256: "562ae0fec3c519b0ea17a7aadd7f1b018bf9d830d1fd2faecdee6e1c337baeb9"
tasks:
  - id: T1
    status: done
    red: {command: "python -m pytest tests/test_streaming_pipeline.py::test_pipeline_contract_emits_verified_nodes_and_edges -q -p no:cacheprovider --basetemp .pytest-tmp-pipeline-t1-red", exit: 1}
    green: {command: "python -m pytest tests/test_streaming_pipeline.py::test_pipeline_contract_emits_verified_nodes_and_edges -q -p no:cacheprovider --basetemp .pytest-tmp-pipeline-t1-green", exit: 0}
  - id: T2
    status: done
    red: {command: "python -m pytest tests/test_streaming_pipeline.py::test_pipeline_rule_fires_only_for_observed_blind_spot -q -p no:cacheprovider --basetemp .pytest-tmp-pipeline-t2-red", exit: 1}
    green: {command: "python -m pytest tests/test_streaming_pipeline.py::test_pipeline_rule_fires_only_for_observed_blind_spot -q -p no:cacheprovider --basetemp .pytest-tmp-pipeline-t2-green", exit: 0}
  - id: T4
    status: done
    red: {command: "python -m pytest tests/test_fixtures_golden_streaming_pipeline.py::test_streaming_pipeline_fixture_corpus_is_complete -q -p no:cacheprovider --basetemp .pytest-tmp-pipeline-t4-corpus-red", exit: 1}
    green: {command: "python -m pytest tests/test_fixtures_golden_streaming_pipeline.py -q -p no:cacheprovider --basetemp .pytest-tmp-pipeline-t4-green2", exit: 0}
  - id: T5
    status: done
    red: {command: "python scripts/check_status_numbers.py --strict", exit: 1}
    green: {command: "python -m pytest tests/test_docs_coverage.py::test_manifest_counts_match_measurements tests/test_docs_coverage.py::test_streaming_coverage_mentions_slo_evaluation tests/test_docs_coverage.py::test_streaming_transport_slo_coverage_mentions_transport_key -q -p no:cacheprovider --basetemp .pytest-tmp-pipeline-t5-green", exit: 0}
claims:
  - text: "Selectors exactos produzem nodes únicos e edges verified somente com endpoints verificados."
    evidence_ref: "tests/test_streaming_pipeline.py::test_pipeline_contract_emits_verified_nodes_and_edges"
  - text: "SF-STREAM-015 dispara somente para streaming.pipeline.unresolved observado."
    evidence_ref: "tests/test_streaming_pipeline.py::test_pipeline_rule_fires_only_for_observed_blind_spot"
  - text: "Core, CLI e MCP preservam o mesmo envelope no mode pipeline."
    evidence_ref: "tests/test_streaming_pipeline.py::test_pipeline_cli_mcp_envelopes_match"
  - text: "O corpus cobre completo, ausente, ambíguo e contrato inválido com facts/findings determinísticos."
    evidence_ref: "tests/test_fixtures_golden_streaming_pipeline.py::test_streaming_pipeline_fixture_goldens"
  - text: "Documentação e contadores medidos estão alinhados."
    evidence_ref: "tests/test_docs_coverage.py::test_manifest_counts_match_measurements"
  - text: "A medição dinâmica de snippets exercita o novo derivador e mantém a enumeração documental íntegra."
    evidence_ref: "tests/test_harness_untrusted.py::TestQuaisExtratoresCarregamTextoDeTerceiro::test_a_enumeracao_do_documento_bate_com_a_medida"
  - text: "As builds do wheel são reproduzíveis, mas a paridade instalada preserva uma dívida de goldens anterior ao pipeline."
    evidence_ref: "scripts/verify_wheel.py; subset local de goldens de Iceberg/CloudWatch/consumers/Glue/scan/scenarios"
change_id: null
---

# STREAMING_END_TO_END_PIPELINE — relatório do build

## Desvios do plano

- A paridade core/CLI/MCP foi implementada junto de T1; AC4 fica explicitamente
  guardada contra fabricar um red artificial e o teste dedicado permanece no
  lote focado de validação.
- O primeiro golden T4 revelou colisão de `Fact.id`: nodes/edges diferentes
  compartilhavam subject e measures. Subjects passaram a carregar identidade
  determinística por node, edge, summary e unresolved reason antes dos goldens
  finais serem regenerados.
- Nenhum collector live, tool MCP ou verbo novo foi criado; o modo reutiliza o
  compositor existente.

## Resultado

T1–T5 concluídas. A implementação mantém match exato, fail-closed, provenance,
`source_fact_ids`, CLI/MCP paritários e regra evidence-first. Goldens são
regenerados por `scripts/regen_streaming_pipeline_fixtures.py` a partir das
entradas commitadas. O escopo não inclui descoberta de topologia, causalidade,
latência, throughput, custo, saúde, exactly-once, replay ou validação funcional.

Gates adicionais exigidos por `docs/gates-por-mudanca.md` passaram: a medição
de snippets (`tests/test_harness_untrusted.py`) fechou com **4 passed** em
155,57s; os gates de runtime scope fecharam com **823 passed** em 212,02s;
agents parity fechou com **186 passed** em 23,90s; surface lock, sync de mirrors,
referências geradas, knowledge lock e bundle offline (70/70) fecharam sem
divergência. `verify_wheel.py` foi repetido com diretório temporário isolado
após a primeira tentativa encontrar `WinError 5` no diretório temporário global.
Na repetição, as duas builds foram byte-identical, mas a paridade instalada
terminou com **47 failed, 3467 passed, 5 skipped** em 1:06:06. O subset no
checkout reproduziu as mesmas 47 falhas em goldens de `iceberg.snapshot`,
`glue.streaming.runtime.unresolved`, scan e cobertura de cenários que esperam
catálogo 208; a mudança do pipeline não toca esses domínios e nenhum golden
fora do escopo foi regenerado.
