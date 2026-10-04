---
sdd: 1
feature: STREAMING_FLINK_SOURCE_SINK_ARTIFACTS
phase: build_report
profile: dev
status: done
upstream:
  path: docs/sdd/STREAMING_FLINK_SOURCE_SINK_ARTIFACTS/plan.md
  sha256: "00b55a2540cc02d80f0db9a080c95c4fc48a45b6a258d9ee40aa3f2ef777af53"
tasks:
  - id: T1
    status: done
    red: {command: "python -m pytest tests/test_facts_flink.py -q", exit: 1}
    green: {command: "python -m pytest tests/test_facts_flink.py -q --basetemp=E:\\projetos\\spark-forge-aws\\.pytest-tmp-flink", exit: 0}
  - id: T2
    status: done
    red: {command: "python -m pytest tests/test_fixtures_golden_flink.py::test_flink_fixture_corpus_is_complete -q", exit: 1}
    green: {command: "python -m pytest tests/test_facts_flink.py tests/test_fixtures_golden_flink.py tests/test_fixtures_kind_coverage.py -q --basetemp=E:\\projetos\\spark-forge-aws\\.pytest-tmp-flink-golden", exit: 0}
  - id: T3
    status: done
    red: {command: "python -m pytest tests/test_docs_coverage.py::test_flink_source_sink_artifacts_coverage -q", exit: 1}
    green: {command: "python -m pytest tests/test_docs_coverage.py::test_flink_source_sink_artifacts_coverage -q --basetemp=E:\\projetos\\spark-forge-aws\\.pytest-tmp-flink-docs", exit: 0}
claims:
  - text: "O extrator preserva source e sink explícitos, aliases e medidas observadas sem preencher campos ausentes."
    evidence_ref: "tests/test_facts_flink.py::test_flink_dump_emits_explicit_source_and_sink"
  - text: "Ausência e formato inválido de endpoints permanecem unresolved com razões nomeadas."
    evidence_ref: "tests/test_facts_flink.py::test_flink_source_sink_absence_is_unresolved"
  - text: "O corpus Flink e o inventário de kinds permanecem determinísticos após a extensão."
    evidence_ref: "tests/test_fixtures_golden_flink.py::test_flink_fixture_corpus_is_complete"
  - text: "Skill, knowledge, README e prompt coverage documentam o contrato sem nova superfície."
    evidence_ref: "tests/test_docs_coverage.py::test_flink_source_sink_artifacts_coverage"
change_id: null
---

# STREAMING_FLINK_SOURCE_SINK_ARTIFACTS — relatório do build

O build adiciona `flink.source` e `flink.sink` ao extrator Apache Flink já
existente. O helper aceita objeto ou lista, preserva atributos escalares e uma
lista fechada de medidas numéricas e emite `flink.unresolved` para ausência,
formato inválido ou registro sem campos. Managed Flink não mudou.

## Validação

Os testes unitários passaram (`8 passed`). O lote de fatos, goldens e cobertura
de kinds passou (`83 passed`). O teste documental específico também passou. A
primeira execução sem `--basetemp` encontrou `PermissionError` no diretório
temporário global do ambiente Windows; os comandos verdes usam diretório
temporário explícito no workspace e não alteram o produto.

Nenhuma regra, tool CLI ou tool MCP nova foi criada. O corpus positivo agora
contém source Kafka e sink Iceberg; fixtures sem endpoints preservam a lacuna
como unresolved.

## Limites

Contadores não são throughput sem timestamp e janela. `delivery_semantics` é
declaração observada, não prova exactly-once. A entrega não coleta runtime,
CloudWatch, savepoint, backlog temporal, causalidade, custo, capacidade ou
validação funcional.
