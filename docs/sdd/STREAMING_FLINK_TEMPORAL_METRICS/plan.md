---
sdd: 1
feature: STREAMING_FLINK_TEMPORAL_METRICS
phase: plan
profile: dev
status: ready
upstream:
  path: docs/sdd/STREAMING_FLINK_TEMPORAL_METRICS/design.md
  sha256: "63f8635a42d4235c6fc81f725a327b5e8523557a8cf347286c25d251e63df61f"
tasks:
  - id: T1
    files: [tests/test_facts_flink.py, sparkforge_aws/facts/flink.py]
    covers: [AC1, AC6]
    test: {path: tests/test_facts_flink.py, name: test_flink_temporal_metrics_preserve_observed_value_and_metadata}
  - id: T2
    files: [tests/test_facts_flink.py, sparkforge_aws/facts/flink.py]
    covers: [AC2]
    test: {path: tests/test_facts_flink.py, name: test_flink_temporal_metric_missing_timestamp_is_unresolved}
  - id: T3
    files: [tests/test_facts_flink.py, sparkforge_aws/facts/flink.py]
    covers: [AC3]
    test: {path: tests/test_facts_flink.py, name: test_flink_temporal_metrics_invalid_shape_is_unresolved}
  - id: T4
    files: [tests/test_fixtures_golden_flink.py, fixtures/flink/flink_temporal_metrics/input/dump.json, fixtures/flink/flink_temporal_metrics/meta.yaml, fixtures/flink/flink_temporal_metrics/expected/facts.json, fixtures/flink/flink_temporal_metrics/expected/findings.json]
    covers: [AC4]
    test: {path: tests/test_fixtures_golden_flink.py, name: test_flink_fixture_corpus_is_complete}
  - id: T5
    files: [skills/analyze-flink-job/SKILL.md, knowledge/flink-streaming.md, README.md, GUIA_DE_USO.md, PROMPT_INICIAL_MESTRE.md, docs/guia/05-agents-e-skills.md, docs/guia/06-extrair-julgar-compor.md, docs/streaming/prompt-coverage.md, docs/guia/referencia/skills/analyze-flink-job.md, .claude/skills/analyze-flink-job/SKILL.md, .agents/skills/analyze-flink-job/SKILL.md, docs/surface.lock.json, knowledge/offline-manifest.json, docs/superpowers/STATUS.md, docs/EVOLUTION-CURRENT.md, docs/DELIVERY-LEDGER.md]
    covers: [AC5]
    test: {path: tests/test_reference_docs.py, name: test_referencia_em_dia}
---

# STREAMING_FLINK_TEMPORAL_METRICS — plano

Implementação serializada em TDD. Cada tarefa começa pelo teste vermelho
específico, aplica somente a mudança primária e repete o mesmo teste verde.
Nenhuma tarefa cria tool ou chama provider.

## T1 — observação temporal válida

Adicionar `test_flink_temporal_metrics_preserve_observed_value_and_metadata`
em `tests/test_facts_flink.py`. O payload deve conter `metrics` com
`metricName`, `value`, `timestamp`, `unit`, `statistic`, `scope` e
`operatorId`, além de uma lista aninhada que não pode entrar em `attrs`.
Antes do código o teste falha porque não existe `flink.metric`.

Implementar em `sparkforge_aws/facts/flink.py`:

```python
EMITTED_KINDS = frozenset({
    "flink.job", "flink.operator", "flink.source", "flink.sink",
    "flink.checkpoint", "flink.state", "flink.metric",
    "flink.unresolved", "flink.analyzed",
    "managed_flink.application", "managed_flink.config",
    "managed_flink.connector", "managed_flink.metric",
    "managed_flink.unresolved", "managed_flink.analyzed",
})

def _flink_metric_facts(data, artifact, line, provenance):
    if "metrics" not in data:
        return []
    raw = data["metrics"]
    if isinstance(raw, dict) and "observations" in raw:
        records = raw["observations"]
    elif isinstance(raw, dict) and any(key in raw for key in ("name", "metric_name", "metricName")):
        records = [raw]
    elif isinstance(raw, list):
        records = raw
    else:
        return [_unresolved(artifact, line, provenance, "flink", "metrics_not_a_list")]
    if not isinstance(records, list) or not records:
        return [_unresolved(artifact, line, provenance, "flink", "metrics_missing")]
    facts = []
    for metric in records:
        if not isinstance(metric, dict):
            facts.append(_unresolved(artifact, line, provenance, "flink", "invalid_metric_record"))
            continue
        name = _value(metric, "name", "metric_name", "metricName")
        value = _number(_value(metric, "value", "metric_value", "metricValue"))
        observed_at = _value(metric, "observed_at", "observedAt", "timestamp", "time")
        if not isinstance(name, str) or not name.strip():
            facts.append(_unresolved(artifact, line, provenance, "flink", "metric_name_missing"))
            continue
        if value is None:
            facts.append(_unresolved(artifact, line, provenance, "flink", "metric_value_invalid"))
            continue
        if observed_at is None:
            facts.append(_unresolved(artifact, line, provenance, "flink", "metric_timestamp_missing"))
            continue
        if not isinstance(observed_at, str) or not observed_at.strip():
            facts.append(_unresolved(artifact, line, provenance, "flink", "metric_timestamp_invalid"))
            continue
        attrs = {"name": name.strip(), "observed_at": observed_at}
        unit = _value(metric, "unit")
        stat = _value(metric, "stat", "statistic")
        scope = _value(metric, "scope")
        operator_id = _value(metric, "operator_id", "operatorId")
        if isinstance(unit, str) and unit:
            attrs["unit"] = unit
        if isinstance(stat, str) and stat:
            attrs["stat"] = stat
        if isinstance(scope, str) and scope:
            attrs["scope"] = scope
        if isinstance(operator_id, str) and operator_id:
            attrs["operator_id"] = operator_id
        reserved = {
            "name", "metric_name", "metricName", "value", "metric_value",
            "metricValue", "observed_at", "observedAt", "timestamp", "time",
            "unit", "stat", "statistic", "scope", "operator_id", "operatorId",
        }
        for key, raw_value in metric.items():
            if key in reserved or raw_value is None or isinstance(raw_value, (dict, list)):
                continue
            if isinstance(raw_value, (str, int, float, bool)):
                attrs[str(key)] = raw_value
        facts.append(_fact("flink.metric", artifact, line, provenance, measures={"value": value}, attrs=attrs, symbol=name.strip()))
    return facts
```

Call helper in `_flink_record` only after existing upstream facts and before
`flink.analyzed`; do not call it in `_managed_record`.

```bash
python -m pytest tests/test_facts_flink.py::test_flink_temporal_metrics_preserve_observed_value_and_metadata -q --basetemp .pytest-flink-temporal-t1
```

## T2 — timestamp ausente

Adicionar `test_flink_temporal_metric_missing_timestamp_is_unresolved` com nome
e valor válidos, sem timestamp. O mesmo teste falha antes e passa depois quando
o helper publica `metric_timestamp_missing` e não publica `flink.metric`.

```bash
python -m pytest tests/test_facts_flink.py::test_flink_temporal_metric_missing_timestamp_is_unresolved -q --basetemp .pytest-flink-temporal-t2
```

## T3 — shape/valor inválido

Adicionar `test_flink_temporal_metrics_invalid_shape_is_unresolved` com
`metrics` escalar e valor não numérico. O teste verifica razões nomeadas e
ausência de zero/fact parcial. Não aceitar timestamp numérico como substituto.

```bash
python -m pytest tests/test_facts_flink.py::test_flink_temporal_metrics_invalid_shape_is_unresolved -q --basetemp .pytest-flink-temporal-t3
```

## T4 — corpus golden

Adicionar `flink_temporal_metrics` ao conjunto obrigatório e criar:

```json
{
  "job": {"name": "orders", "version": "1.20.1"},
  "checkpoints": [{"id": 12, "status": "COMPLETED", "duration_ms": 840}],
  "metrics": [
    {"name": "busyTimeMsPerSecond", "value": 750, "observed_at": "2026-10-03T00:00:00Z", "unit": "MillisecondsPerSecond", "stat": "Average", "scope": "operator", "operator_id": "aggregate", "labels": {"drop": true}},
    {"metricName": "backpressuredRatio", "value": 0.12, "timestamp": "2026-10-03T00:00:00Z", "unit": "Ratio", "statistic": "Average", "scope": "operator", "operatorId": "aggregate"},
    {"name": "lateRecordsPerSecond", "value": 4.0, "unit": "CountPerSecond"}
  ]
}
```

O meta declara kinds `flink.analyzed`, `flink.checkpoint`, `flink.job`,
`flink.metric` e `flink.unresolved`. A ausência de source/sink e o terceiro
metric preservam unresolved já nomeado. Rodar primeiro o teste do corpus para
ver o vermelho por fixture/golden ausente; depois:

```bash
python scripts/regen_flink_fixtures.py
python -m pytest tests/test_fixtures_golden_flink.py -q --basetemp .pytest-flink-temporal-t4
```

## T5 — knowledge, skill e distribuição

Atualizar skill fonte para listar `flink.metric`, explicar o contrato temporal
upstream e manter Managed separado; atualizar knowledge, README, guias, prompt,
coverage, ledger/status. Regenerar mirrors e referência, recalcular
`knowledge/offline-manifest.json` e `docs/surface.lock.json`. Não adicionar URL,
tool ou verbo.

```bash
python scripts/sync_skills.py
python scripts/gen_reference_docs.py
python scripts/check_surface_lock.py --update
python scripts/check_status_numbers.py --strict
python scripts/verify_offline_bundle.py --check
python -m pytest tests/test_reference_docs.py::test_referencia_em_dia -q --basetemp .pytest-flink-temporal-t5
```
