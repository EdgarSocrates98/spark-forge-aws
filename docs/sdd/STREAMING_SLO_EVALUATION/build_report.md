---
sdd: 1
feature: STREAMING_SLO_EVALUATION
phase: build_report
profile: dev
status: done
upstream:
  path: docs/sdd/STREAMING_SLO_EVALUATION/plan.md
  sha256: "fc3e830a73a16e6502f52c3d822edc3a136aab9f62c563f4d08f73cb63b5fae2"
tasks:
  - id: T1
    status: done
    red: {command: "python -m pytest tests/test_facts_streaming_slo.py -q", exit: 1}
    green: {command: "python -m pytest tests/test_facts_streaming_slo.py -q --basetemp=.pytest-tmp-slo", exit: 0}
  - id: T2
    status: done
    red: {command: "python -m pytest tests/test_facts_streaming_slo.py -q (prerequisite module absent)", exit: 1}
    green: {command: "python -m pytest tests/test_streaming_rules.py::test_slo_evaluation_rules_are_evidence_first -q", exit: 0}
  - id: T3
    status: done
    red: {command: "python -m pytest tests/test_facts_streaming_slo.py -q (prerequisite module absent)", exit: 1}
    green: {command: "python -m pytest tests/test_analyze_streaming_composition.py -q", exit: 0}
  - id: T4
    status: done
    red: {command: "python -m pytest tests/test_facts_streaming_slo.py -q (prerequisite module absent)", exit: 1}
    green: {command: "python -m pytest tests/test_fixtures_golden_streaming_composition.py -q", exit: 0}
  - id: T5
    status: done
    red: {command: "python -m pytest tests/test_facts_streaming_slo.py -q (prerequisite module absent)", exit: 1}
    green: {command: "python -m pytest tests/test_docs_coverage.py::test_streaming_coverage_mentions_slo_evaluation -q", exit: 0}
  - id: T6
    status: done
    red: {command: "python -m pytest tests/test_facts_streaming_slo.py -q (prerequisite module absent)", exit: 1}
    green: {command: "python -m pytest tests/test_surface_lock.py::TestOLockBateComAMedida::test_the_tool_catalogue_matches -q", exit: 0}
claims:
  - text: "mode=slo compõe uma declaração streaming.slo com métricas diretamente observadas em streaming.progress.batch e separa met, violated e unresolved sem inferir sucesso por ausência de evidência."
    evidence_ref: "sparkforge/facts/streaming_slo.py; tests/test_facts_streaming_slo.py"
  - text: "SF-STREAM-011 julga somente violação SLO observada e SF-STREAM-012 preserva a barreira de evidência como finding estrutural."
    evidence_ref: "rules/catalog/streaming-operations.yaml; tests/test_streaming_rules.py::test_slo_evaluation_rules_are_evidence_first"
  - text: "CLI e MCP usam o mesmo core read-only para mode=slo."
    evidence_ref: "tests/test_analyze_streaming_composition.py::test_slo_cli_and_mcp_envelopes_match"
  - text: "Goldens met, violated e unresolved cobrem facts, findings, unresolved e regressão dos modos existentes."
    evidence_ref: "fixtures/streaming_composition/slo_*; tests/test_fixtures_golden_streaming_composition.py"
  - text: "Knowledge, skill, mirrors, referências, surface lock, offline manifest, sources lock e números correntes foram atualizados."
    evidence_ref: "scripts/sync_skills.py; scripts/gen_reference_docs.py; scripts/check_surface_lock.py; scripts/check_status_numbers.py --strict"
change_id: null
---

# STREAMING_SLO_EVALUATION — relatório do build

## Resultado

Build concluído em T1–T6. A implementação permanece offline e determinística:
compara targets declarados com observações diretamente presentes em batches de
Structured Streaming, exige cobertura temporal e publica a ausência de
evidência como `streaming.slo.unresolved`.

## Decisões e limites preservados

- Métricas aceitas são somente `input_rows_per_second`,
  `processed_rows_per_second`, `batch_duration_ms` e `num_input_rows`.
- Operadores aceitos são `lt`, `lte`, `gt`, `gte` e `eq`; unidades não são
  convertidas e janelas não são preenchidas por ordem de arquivo.
- `met` exige que todos os valores observados passem; `violated` exige ao menos
  uma observação fora do comparador. Nenhum status prova disponibilidade,
  causa, custo, p95, freshness ou saúde end-to-end.
- O catálogo já usava `SF-STREAM-010` para OpenLineage; por isso os novos
  achados são `SF-STREAM-011` e `SF-STREAM-012`.
- A suíte completa não foi executada nesta fase, conforme o escopo solicitado.

## Revisão por tarefa

- **T1:** extrator derivado seleciona SLO por nome/unicidade, valida identidade,
  métrica, unidade, timestamp, quantidade e cobertura; 10 testes verdes.
- **T2:** regras evidence-first preservam evidências e recusam causalidade ou
  custo; regra positiva e estrutural cobertas.
- **T3:** CLI, MCP e core compartilham o envelope `mode=slo` e `slo_name`.
- **T4:** três fixtures novas cobrem `met`, `violated`, janela não coberta,
  facts derivados e findings.
- **T5:** skill, knowledge, prompt coverage e referências geradas descrevem a
  avaliação observada e seus limites.
- **T6:** surface lock, manifesto de regras, offline manifest, sources lock,
  mirrors e números correntes foram reconciliados.

## Evidência de gates

- 16 testes focados de fatos, regras e portas; 2 goldens da composição.
- 919 testes de cobertura de kinds e reachability; 4 testes de snippet measure.
- 40 testes de docs/referências/surface após corrigir `manifest.json` para 212
  regras; `sync_skills`, referências geradas, surface lock, status numbers,
  bundle offline e SDD check verdes.

Não há medição de performance, custo, throughput, latência ou capacidade cloud.
