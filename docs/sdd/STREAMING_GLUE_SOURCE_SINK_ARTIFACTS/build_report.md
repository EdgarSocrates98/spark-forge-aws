---
sdd: 1
feature: STREAMING_GLUE_SOURCE_SINK_ARTIFACTS
phase: build_report
profile: dev
status: done
upstream:
  path: docs/sdd/STREAMING_GLUE_SOURCE_SINK_ARTIFACTS/plan.md
  sha256: "633d4d94566286bbe780e4890b10cf43b0078203dab0e292e3bedcc16c3f0912"
tasks:
  - id: T1
    status: done
    red: {command: "python -m pytest tests/test_facts_glue_streaming.py -q --basetemp=E:\\projetos\\spark-forge-aws\\.pytest-tmp-glue-source-sink", exit: 1}
    green: {command: "python -m pytest tests/test_facts_glue_streaming.py -q --basetemp=E:\\projetos\\spark-forge-aws\\.pytest-tmp-glue-source-sink", exit: 0}
  - id: T2
    status: done
    red: {command: "python -m pytest tests/test_fixtures_golden_glue_streaming.py tests/test_fixtures_kind_coverage.py -q --basetemp=E:\\projetos\\spark-forge-aws\\.pytest-tmp-glue-golden-2", exit: 1}
    green: {command: "python -m pytest tests/test_fixtures_golden_glue_streaming.py tests/test_fixtures_kind_coverage.py -q --basetemp=E:\\projetos\\spark-forge-aws\\.pytest-tmp-glue-golden-2", exit: 0}
  - id: T3
    status: done
    red: {command: "python -m pytest tests/test_docs_coverage.py::test_glue_source_sink_artifacts_coverage -q --basetemp=E:\\projetos\\spark-forge-aws\\.pytest-tmp-glue-docs", exit: 1}
    green: {command: "python -m pytest tests/test_facts_glue_streaming.py tests/test_glue_streaming_rules.py tests/test_fixtures_golden_glue_streaming.py tests/test_analyze_glue_streaming.py tests/test_docs_coverage.py::test_glue_source_sink_artifacts_coverage -q --basetemp=E:\\projetos\\spark-forge-aws\\.pytest-tmp-glue-final", exit: 0}
claims:
  - text: "O extrator emite source e sink explícitos para objeto/lista, preserva whitelist escalar e medidas fechadas sem preencher lacunas."
    evidence_ref: "tests/test_facts_glue_streaming.py::test_stream_endpoints_emit_explicit_facts"
  - text: "Aliases singulares, booleanos escalares e shape inválido permanecem cobertos pelo contrato."
    evidence_ref: "tests/test_facts_glue_streaming.py::test_stream_endpoints_preserve_observed_fields_only"
  - text: "Ausência e shape inválido produzem unresolved nomeado."
    evidence_ref: "tests/test_facts_glue_streaming.py::test_stream_endpoint_absence_is_unresolved"
  - text: "Corpus, regras existentes, analyzer e documentação permanecem determinísticos."
    evidence_ref: "tests/test_fixtures_golden_glue_streaming.py::test_glue_streaming_fixture_corpus_is_complete"
change_id: null
---

# STREAMING_GLUE_SOURCE_SINK_ARTIFACTS — relatório do build

O build adiciona `glue.streaming.source` e `glue.streaming.sink` ao extrator
Glue Streaming já existente. O helper aceita objeto ou lista sob `stream`,
preserva somente atributos escalares permitidos e medidas numéricas fechadas e
emite `glue.streaming.unresolved` para ausência, shape inválido, registro
inválido ou falta de métrica. O namespace existente de job/runtime/analyzed e
as regras RTM não mudaram.

## Validação

- Facts unitários: `6 passed`.
- Corpus Glue Streaming, goldens, regras e cobertura de kinds: `73 passed`.
- Facts, regras, goldens, analyzer CLI/MCP e cobertura documental: `15 passed`.
- `python scripts/verify_offline_bundle.py --check`: `checked: 69`, sem falhas
  após atualização dos hashes de `knowledge/INDEX.md` e
  `knowledge/glue-streaming-rtm.md`.
- `python scripts/check_surface_lock.py`: `0 divergencia(s)` após declarar o
  crescimento de payload documental.
- Suíte completa não executada por escopo desta fase.

## Limites

Os endpoints são evidência de definição offline, não prova de execução live,
throughput, backlog temporal, latência, exactly-once, capacidade, custo ou
correção funcional. Nenhuma regra nova ou operação CLI/MCP foi necessária.
