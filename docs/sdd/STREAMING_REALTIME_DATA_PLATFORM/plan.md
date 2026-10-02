---
sdd: 1
feature: STREAMING_REALTIME_DATA_PLATFORM
phase: plan
profile: dev
status: ready
upstream:
  path: docs/sdd/STREAMING_REALTIME_DATA_PLATFORM/design.md
  sha256: "79d221d3db5ae647b26d1fa7492519ae0c39693598631a4c098cc8b677a3f6e3"
tasks:
  - id: T1
    files: [tests/test_facts_streaming.py, sparkforge/facts/pyspark_ast.py, tests/test_fixtures_kind_coverage.py, tests/test_rules_catalog_reachability.py]
    covers: [AC1, AC7]
    test: {path: tests/test_facts_streaming.py, name: test_extract_structured_streaming_source_emits_anchored_facts}
  - id: T2
    files: [tests/test_facts_streaming.py, sparkforge/facts/streaming.py]
    covers: [AC2, AC3, AC7]
    test: {path: tests/test_facts_streaming.py, name: test_extract_streaming_progress_emits_batch_source_sink_and_state_facts}
  - id: T3
    files: [tests/test_streaming_rules.py, rules/catalog/streaming.yaml, rules/catalog/routing.yaml, agents/spark-performance-architect.md, .agents/agents/spark-performance-architect.md, .claude/agents/spark-performance-architect.md]
    covers: [AC4]
    test: {path: tests/test_streaming_rules.py, name: test_streaming_rules_require_runtime_and_sufficient_evidence}
  - id: T4
    files: [tests/test_fixtures_golden_streaming.py, fixtures/streaming/streaming_source.py, fixtures/streaming/batch_only.py, fixtures/streaming/progress_positive.jsonl, fixtures/streaming/progress_single.jsonl, fixtures/streaming/progress_malformed.jsonl, fixtures/streaming/meta.yaml]
    covers: [AC3, AC5, AC7]
    test: {path: tests/test_fixtures_golden_streaming.py, name: test_all_required_fixtures_exist}
  - id: T5
    files: [tests/test_analyze_streaming.py, sparkforge/adapters/_core.py, sparkforge/adapters/cli.py, sparkforge/adapters/tools.py]
    covers: [AC6]
    test: {path: tests/test_analyze_streaming.py, name: test_cli_and_core_emit_identical_streaming_envelope}
  - id: T6
    files: [knowledge/streaming-reliability.md, knowledge/INDEX.md, knowledge/offline-manifest.json, knowledge/sources.lock.json, manifest.json]
    covers: [AC4, AC8]
    test: {path: tests/test_offline_expansion.py, name: test_offline_manifest_verifies_without_network}
  - id: T7
    files: [docs/surface.lock.json, docs/guia/referencia/cli/analyze.md, docs/guia/referencia/tools/sparkforge_analyze_streaming.md, docs/guia/referencia/tools/README.md]
    covers: [AC8]
    test: {path: tests/test_reference_docs.py, name: test_referencia_em_dia}

---

# STREAMING_REALTIME_DATA_PLATFORM — plano

## T1 — source Structured Streaming aditivo

Teste primeiro em `tests/test_facts_streaming.py`: chamar `extract_source` sobre
`readStream.format(...).load()`, `writeStream...start()`, `option`, `trigger`,
`withWatermark`, `dropDuplicates`, join, stateful aggregation e `foreachBatch`; exigir
facts `streaming.*`, `subject.file`, linha positiva e provenance. O mesmo teste deve rodar
um código `spark.read...write...` batch e exigir zero kinds `streaming.*`.

Rodar:

```bash
python -m pytest tests/test_facts_streaming.py::test_extract_structured_streaming_source_emits_anchored_facts -q
```

O vermelho esperado é `ImportError`/`AssertionError` porque os kinds ainda não existem.
Implementar o detector estático em `sparkforge/facts/pyspark_ast.py`, preservando todos os
kinds atuais, adicionando os kinds ao `EMITTED_KINDS`, usando `_subject` e emitindo
`streaming.module_analyzed` como sentinela. Registrar o módulo nos dois inventários manuais.

Rodar o mesmo comando até verde; depois:

```bash
python -m pytest tests/test_rules_catalog_reachability.py tests/test_fixtures_kind_coverage.py -q
git add sparkforge/facts/pyspark_ast.py tests/test_facts_streaming.py tests/test_fixtures_kind_coverage.py tests/test_rules_catalog_reachability.py
git commit -m "feat(streaming): extract structured streaming source facts"
```

## T2 — StreamingQueryProgress offline

Teste primeiro em `tests/test_facts_streaming.py`: ler JSONL positivo e exigir batch/source/
sink/event-time/state facts, batch ids e medidas em ms/rows/rows-per-second; ler uma linha
única e exigir `streaming.progress.unresolved` com `insufficient_series`, sem fact de série
julgável; repetir a extração e comparar `to_dict()` byte a byte.

```bash
python -m pytest tests/test_facts_streaming.py::test_extract_streaming_progress_emits_batch_source_sink_and_state_facts tests/test_facts_streaming.py::test_insufficient_progress_is_unresolved_not_a_trend -q
```

O vermelho esperado é `ModuleNotFoundError: sparkforge.facts.streaming`. Implementar
`extract_streaming_progress_path`, `extract_streaming_progress_tree` e `extract_streaming_progress_text`
sem rede, aceitando JSON, lista de progressos e JSONL; parsear somente campos documentados;
registrar linha/arquivo no subject; preservar ordem observada em `observed_index`; emitir
unresolved para JSON inválido, shape desconhecido, campo obrigatório ausente e série curta.

```bash
python -m pytest tests/test_facts_streaming.py -q
```

Gates: `tests/test_rules_catalog_reachability.py`, `tests/test_fixtures_kind_coverage.py`.

```bash
git add sparkforge/facts/streaming.py tests/test_facts_streaming.py
git commit -m "feat(streaming): extract streaming query progress"
```

## T3 — catálogo, runtime e roteamento

Teste primeiro em `tests/test_streaming_rules.py`: carregar o catálogo e julgar facts
positivos com `RuntimeContext`; exigir finding com evidence não vazia e `rule_id` SF-STREAM;
repetir sem runtime e com uma série insuficiente e exigir zero finding, com unresolved
preservado. Incluir fronteira negativa para não usar os thresholds legados de Kafka/Kinesis.

```bash
python -m pytest tests/test_streaming_rules.py::test_streaming_rules_require_runtime_and_sufficient_evidence -q
```

O vermelho esperado é regra ausente ou catálogo inalcançável. Criar `rules/catalog/streaming.yaml`
com area `SF-STREAM`, `runtime_scope: {}`, `requires_facts`, `when` sobre fatos estruturais
e séries observadas, fonte oficial, action fechada, riscos, tradeoffs, validation e rollback.
Adicionar `SF-STREAM` ao `spark-performance-architect`, regenerar os dois espelhos com
`python scripts/sync_skills.py`, e inserir uma rota `AGENT-090` por `findings_area` em
`rules/catalog/routing.yaml`.

```bash
python -m pytest tests/test_streaming_rules.py tests/test_router_agents.py tests/test_case_router.py -q
python scripts/sync_skills.py --check
git add rules/catalog/streaming.yaml rules/catalog/routing.yaml agents/spark-performance-architect.md .agents/agents/spark-performance-architect.md .claude/agents/spark-performance-architect.md tests/test_streaming_rules.py
git commit -m "feat(streaming): add evidence guarded rules and routing"
```

## T4 — corpus golden

Teste primeiro em `tests/test_fixtures_golden_streaming.py`: declarar `FIXTURES`, carregar
`meta.yaml`, extrair código e progress em caminhos separados, julgar com runtime declarado,
validar Facts/Findings, e conferir que o conjunto contém positivo, negativo, unresolved e
runtime divergente. Os expected facts/findings são comparados por `to_dict()` e os kinds
em `meta.yaml` são conferidos.

```bash
python -m pytest tests/test_fixtures_golden_streaming.py::test_all_required_fixtures_exist -q
```

O vermelho esperado é fixture ausente ou expected rule mismatch. Criar as cinco entradas
do corpus e o runner determinístico; não citar holdout. O caso divergente deve produzir
runtime mismatch/unresolved, não ser reinterpretado por um default.

```bash
python -m pytest tests/test_fixtures_golden_streaming.py tests/test_fixtures_kind_coverage.py -q
git add fixtures/streaming tests/test_fixtures_golden_streaming.py
git commit -m "test(streaming): add golden corpus for source and progress"
```

## T5 — contrato CLI/MCP

Teste primeiro em `tests/test_analyze_streaming.py`: chamar `_core.analyze_streaming` e
`call_tool("sparkforge_analyze_streaming", ...)` com o mesmo source e progress, comparar
envelope, `by_kind`, unresolved e ids; construir CLI com `analyze streaming --artifact` e
conferir saída JSON. Garantir que o path não é importado/executado.

```bash
python -m pytest tests/test_analyze_streaming.py::test_cli_and_core_emit_identical_streaming_envelope -q
```

O vermelho esperado é atributo/tool ausente. Adicionar import e função no core, parser e
handler CLI usando `_emit_facts_page`, entrada TOOLS/schema/handler MCP e `_HANDLERS` usando
o mesmo core. `--artifact` é obrigatório e limitado a `source|progress`; o output salvo
continua sendo a lista completa de facts.

```bash
python -m pytest tests/test_analyze_streaming.py tests/test_adapters_tools.py -q
git add sparkforge/adapters/_core.py sparkforge/adapters/cli.py sparkforge/adapters/tools.py tests/test_analyze_streaming.py
git commit -m "feat(streaming): expose unified cli and mcp analysis"
```

## T6 — conhecimento e locks

Editar `knowledge/streaming-reliability.md` e `knowledge/INDEX.md` com envelope, limites,
separação Spark/Glue e URLs oficiais consultadas. Atualizar `manifest.json` com contagens
medidas, não estimadas. Regenerar hashes offline:

```bash
python scripts/refresh_knowledge.py --update --offline
python -m pytest tests/test_refresh_knowledge.py tests/test_offline_expansion.py -q
```

O vermelho esperado é lock ou hash fora de sincronia. Depois rodar `python scripts/verify_offline_bundle.py`
e commitar os documentos/locks/manifest.

```bash
git add knowledge/streaming-reliability.md knowledge/INDEX.md knowledge/offline-manifest.json knowledge/sources.lock.json manifest.json
git commit -m "docs(streaming): anchor structured streaming knowledge"
```

## T7 — referências e surface lock

Regenerar referências e lock a partir dos catálogos reais:

```bash
python scripts/gen_reference_docs.py
python scripts/check_surface_lock.py
python -m pytest tests/test_reference_docs.py tests/test_surface_lock.py -q
```

O vermelho esperado é página velha, tool não documentada ou surface lock divergente.
Commitar somente a saída dos geradores e, por fim, rodar `sparkforge sdd check`.

```bash
git add docs/surface.lock.json docs/guia/referencia
git commit -m "chore(streaming): regenerate public references"
```
