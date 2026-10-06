---
sdd: 1
feature: STREAMING_SLO_LATENCY_FRESHNESS
phase: build_report
profile: dev
status: done
upstream:
  path: docs/sdd/STREAMING_SLO_LATENCY_FRESHNESS/plan.md
  sha256: "71f8b2eca99024b1a473c2710f5d79e43da4254836dcf4f88f308f31902ceed8"
tasks:
  - id: T1
    status: done
    red: {command: "python -m pytest --basetemp=E:\\projetos\\spark-forge-aws\\.pytest-tmp tests/test_facts_streaming_ops.py::test_slo_preserves_statistic_attribute tests/test_facts_streaming.py::test_progress_derives_freshness_only_from_event_time_max -q", exit: 1}
    green: {command: "python -m pytest --basetemp=E:\\projetos\\spark-forge-aws\\.pytest-tmp tests/test_facts_streaming_ops.py::test_slo_preserves_statistic_attribute tests/test_facts_streaming.py::test_progress_derives_freshness_only_from_event_time_max tests/test_facts_streaming.py::test_progress_preserves_explicit_end_to_end_latency -q", exit: 0}
  - id: T2
    status: done
    red: {command: "python -m pytest --basetemp=E:\\projetos\\spark-forge-aws\\.pytest-tmp tests/test_facts_streaming_slo.py::test_evaluates_p95_freshness_slo tests/test_facts_streaming_slo.py::test_end_to_end_latency_requires_explicit_measurement -q", exit: 1}
    green: {command: "python -m pytest --basetemp=E:\\projetos\\spark-forge-aws\\.pytest-tmp tests/test_facts_streaming_slo.py::test_evaluates_p95_freshness_slo tests/test_facts_streaming_slo.py::test_end_to_end_latency_requires_explicit_measurement -q", exit: 0}
  - id: T3
    status: done
    red: {command: "python -m pytest --basetemp=E:\\projetos\\spark-forge-aws\\.pytest-tmp tests/test_fixtures_golden_streaming_composition.py::test_fixture_goldens -q", exit: 1}
    green: {command: "python -m pytest --basetemp=E:\\projetos\\spark-forge-aws\\.pytest-tmp tests/test_fixtures_golden_streaming_composition.py::test_fixture_goldens -q", exit: 0}
  - id: T4
    status: done
    red: {command: "python -m pytest --basetemp=E:\\projetos\\spark-forge-aws\\.pytest-tmp tests/test_docs_coverage.py::test_streaming_slo_latency_freshness_coverage -q", exit: 1}
    green: {command: "python -m pytest --basetemp=E:\\projetos\\spark-forge-aws\\.pytest-tmp tests/test_docs_coverage.py::test_streaming_slo_latency_freshness_coverage -q", exit: 0}
claims:
  - text: "A declaração SLO preserva statistic=all|p95 e rejeita statistic desconhecido sem criar streaming.slo falso."
    evidence_ref: "sparkforge_aws/facts/streaming_ops.py; tests/test_facts_streaming_ops.py::test_slo_preserves_statistic_attribute"
  - text: "Freshness é medida por batch apenas com freshnessMs explícito ou timestamp - eventTime.max timezone-aware e não negativo."
    evidence_ref: "sparkforge_aws/facts/streaming.py; tests/test_facts_streaming.py::test_progress_derives_freshness_only_from_event_time_max"
  - text: "p95 nearest-rank publica observed_p95 e compara o agregado contra o target sem interpolação."
    evidence_ref: "sparkforge_aws/facts/streaming_slo.py; tests/test_facts_streaming_slo.py::test_evaluates_p95_freshness_slo"
  - text: "End-to-end latency não é derivada de batchDuration, watermark ou freshness; só valor explícito é elegível."
    evidence_ref: "tests/test_facts_streaming.py::test_progress_preserves_explicit_end_to_end_latency; tests/test_facts_streaming_slo.py::test_end_to_end_latency_requires_explicit_measurement"
  - text: "Golden p95/freshness e goldens compostos existentes permanecem determinísticos e válidos."
    evidence_ref: "fixtures/streaming_composition/slo_p95_freshness; tests/test_fixtures_golden_streaming_composition.py::test_fixture_goldens"
change_id: null
---

# STREAMING_SLO_LATENCY_FRESHNESS — relatório do build

## Resultado

Build concluído em T1–T4. O contrato `mode=slo` continua sendo o mesmo
compositor offline, agora com `statistic=p95`, `freshness_ms` e
`end_to_end_latency_ms` explicitamente observáveis. A mudança preserva fatos
de origem, identidade, unidade, timestamp, cobertura de janela e
`causal_inference: false`.

## Decisões e limites preservados

- `freshness_ms` derivada é `progress.timestamp - eventTime.max`; `eventTime.avg`
  e watermark não são usados como substitutos.
- `end_to_end_latency_ms` não é inferida de `batchDuration`; somente
  `endToEndLatencyMs` explícito entra na série.
- p95 usa nearest-rank `ceil(0.95*n)`, sem interpolação, confiança,
  extrapolação ou threshold inventado.
- Série parcial, timestamp inválido, `eventTime.max` inválido, unidade errada,
  statistic desconhecido ou janela não coberta permanecem unresolved.
- A suíte completa não foi executada nesta frente; foram executados lotes
  focados e gates derivados da mudança.

## Revisão por tarefa

- **T1:** declaração segura e extração de freshness/latência explícita foram
  cobertas por testes node-level.
- **T2:** avaliação p95 e recusa de end-to-end implícita foram cobertas no
  compositor, mantendo comparadores anteriores.
- **T3:** novo golden `slo_p95_freshness` foi adicionado e goldens compostos
  existentes foram regenerados para refletir facts temporais atuais.
- **T4:** knowledge, skills, mirrors, referências, prompt coverage e testes de
  documentação foram reconciliados.

## Evidência focada

- Lote de fatos, SLO, composição, goldens e docs: **74 passed**.
- `git diff --check`: verde.
- A atualização de surface/manifest não criou tool nova; CLI/MCP continuam
  usando `analyze streaming-composition --mode slo`.
