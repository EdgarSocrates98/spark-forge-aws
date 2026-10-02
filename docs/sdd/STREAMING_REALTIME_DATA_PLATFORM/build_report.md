---
sdd: 1
feature: STREAMING_REALTIME_DATA_PLATFORM
phase: build_report
profile: dev
status: ready
upstream:
  path: docs/sdd/STREAMING_REALTIME_DATA_PLATFORM/plan.md
  sha256: "1ef4e3f76ac6faab455d2d51489aaf6e17e2535a00016374d39c0cb702cfd359"
tasks:
  - id: T1
    status: done
    red:
      command: "python -m pytest tests/test_facts_streaming.py::test_extract_structured_streaming_source_emits_anchored_facts -q --basetemp=.pytest-t1"
      exit: 1
    green:
      command: "python -m pytest tests/test_facts_streaming.py::test_extract_structured_streaming_source_emits_anchored_facts -q --basetemp=.pytest-t1"
      exit: 0
  - id: T2
    status: done
    red:
      command: "python -m pytest tests/test_facts_streaming.py::test_extract_streaming_progress_emits_batch_source_sink_and_state_facts tests/test_facts_streaming.py::test_insufficient_progress_is_unresolved_not_a_trend tests/test_facts_streaming.py::test_streaming_extraction_is_deterministic_and_batch_safe -q --basetemp=.pytest-red-replay-t2-all"
      exit: 1
    green:
      command: "python -m pytest tests/test_facts_streaming.py::test_extract_streaming_progress_emits_batch_source_sink_and_state_facts tests/test_facts_streaming.py::test_insufficient_progress_is_unresolved_not_a_trend tests/test_facts_streaming.py::test_streaming_extraction_is_deterministic_and_batch_safe -q --basetemp=.pytest-t2final"
      exit: 0
  - id: T3
    status: done
    red:
      command: "python -m pytest tests/test_streaming_rules.py::test_streaming_rules_require_runtime_and_sufficient_evidence -q --basetemp=.pytest-t3"
      exit: 1
    green:
      command: "python -m pytest tests/test_streaming_rules.py tests/test_rules_catalog_reachability.py tests/test_router_agents.py tests/test_case_router.py -q --basetemp=.pytest-t3c"
      exit: 0
  - id: T4
    status: done
    red:
      command: "python -m pytest tests/test_fixtures_golden_streaming.py::test_all_required_fixtures_exist -q --basetemp=.pytest-red-replay-t4"
      exit: 4
    green:
      command: "python -m pytest tests/test_facts_streaming.py tests/test_fixtures_golden_streaming.py tests/test_fixtures_kind_coverage.py tests/test_rules_catalog_reachability.py -q --basetemp=.pytest-t4final"
      exit: 0
  - id: T5
    status: done
    red:
      command: "python -m pytest tests/test_analyze_streaming.py::test_cli_and_core_emit_identical_streaming_envelope -q --basetemp=.pytest-red-replay-t5"
      exit: 4
    green:
      command: "python -m pytest tests/test_analyze_streaming.py tests/test_adapters_tools.py::TestToolSurface tests/test_adapters_tools.py::TestOutputSchemasAreReal tests/test_adapters_mcp.py tests/test_adapters_detail_level.py -q --basetemp=.pytest-t5g"
      exit: 0
  - id: T6
    status: done
    red:
      command: "python -m pytest tests/test_refresh_knowledge.py tests/test_offline_expansion.py tests/test_knowledge_drift.py -q --basetemp=.pytest-t6"
      exit: 1
    green:
      command: "python -m pytest tests/test_refresh_knowledge.py tests/test_offline_expansion.py tests/test_knowledge_drift.py -q --basetemp=.pytest-t6b"
      exit: 0
  - id: T7
    status: done
    red:
      command: "python scripts/check_surface_lock.py"
      exit: 1
    green:
      command: "python scripts/check_surface_lock.py"
      exit: 0
claims:
  - text: "Static Structured Streaming facts are anchored to source locations and preserve batch-source separation."
    evidence_ref: "tests/test_facts_streaming.py::test_extract_structured_streaming_source_emits_anchored_facts"
  - text: "StreamingQueryProgress extraction preserves batch order and emits unresolved instead of a trend for insufficient series."
    evidence_ref: "tests/test_facts_streaming.py::test_extract_streaming_progress_emits_batch_source_sink_and_state_facts"
  - text: "Streaming rules require runtime and sufficient observed evidence before findings are emitted."
    evidence_ref: "tests/test_streaming_rules.py::test_streaming_rules_require_runtime_and_sufficient_evidence"
  - text: "CLI and MCP adapters share the streaming analysis envelope through the same core contract."
    evidence_ref: "tests/test_analyze_streaming.py::test_cli_and_core_emit_identical_streaming_envelope"
  - text: "Offline knowledge and generated surface locks are synchronized with the implemented streaming surface."
    evidence_ref: "python scripts/check_surface_lock.py; python scripts/verify_offline_bundle.py --check"
change_id: null
---

# STREAMING_REALTIME_DATA_PLATFORM — relatório do build

## Desvios do plano

Nenhum desvio de implementação. A integração com contratos derivados foi
descoberta depois do T7 e registrada como correção de build: a nova capability
foi adicionada ao `parity.yaml`, o allowlist de paridade MCP/fixtures e o
inventário canônico de kinds foram atualizados, e os goldens derivados de
assessment foram recalculados contra o catálogo medido (177 para 180 regras).
As contagens de superfície passaram a refletir 116 tools em stdio/full e 107
tools que declaram caminho.

## Revisão

Todas as sete tarefas do plano foram executadas em commits separados. A revisão
de especificação e a revisão do diff confirmaram que a primeira onda ficou
restrita ao backbone offline de Structured Streaming e não introduziu collectors
AWS live, thresholds não medidos ou promessa de ganho.

Desvios registrados: T5 usa `tests/test_analyze_streaming.py`, que é o nome real
do teste de contrato após a implementação. Os vermelhos específicos de AC5, AC6
e AC7 foram reproduzidos nos snapshots imediatamente anteriores às tarefas em
`.sdd-red-replay-20261001/`, pois o primeiro registro de T4/T5 usava coleta do
arquivo inteiro e o primeiro T2 não incluía o terceiro teste. T7 valida o surface
lock diretamente porque sua saída é gerada por catálogo, não por uma regra de
negócio. A suíte final em lotes confirmou 5.509 testes e 6 skips no lote
`g-z`; o único teste adicional que falhou nesse lote (`test_integrate.py`) passou
isoladamente com basetemp curto, caracterizando limite de caminho do isolamento
Windows, não falha funcional. O gate histórico `check_vnext_claims.py` continua
recusando 164 referências a commits que não existem neste clone; nenhum claim
histórico foi alterado por esta feature.

Achados da revisão: nenhum crítico ou importante aberto. A cobertura de Kafka,
Kinesis, Flink, CDC, contratos e manutenção de lakehouse continua explicitamente
unresolved e foi deixada para as ondas seguintes do explore.
