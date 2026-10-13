---
sdd: 1
feature: STREAMING_TEMPORAL_EVIDENCE
phase: build_report
profile: dev
status: done
upstream:
  path: docs/sdd/STREAMING_TEMPORAL_EVIDENCE/plan.md
  sha256: "15414ba2fbbcc76c01afdc72c0c0a04e513dc8a3ed4b1a6e23e241ade30b9e85"
tasks:
  - id: T1
    status: done
    red: {command: "python -m pytest tests/test_facts_streaming_temporal.py -q --basetemp=C:/sfpt-temporal-t1-red", exit: 2}
    green: {command: "python -m pytest tests/test_facts_streaming_temporal.py -q --basetemp=C:/sfpt-temporal-t1", exit: 0}
  - id: T2
    status: done
    red: {command: "python -m pytest tests/test_facts_transport.py::test_transport_preserves_observed_timestamp -q --basetemp=C:/sfpt-temporal-t2-red", exit: 1}
    green: {command: "python -m pytest tests/test_facts_transport.py -q --basetemp=C:/sfpt-temporal-t2", exit: 0}
  - id: T3
    status: done
    red: {command: "python -m pytest tests/test_streaming_rules.py::test_temporal_rule_requires_paired_observations -q --basetemp=C:/sfpt-temporal-t3-red", exit: 1}
    green: {command: "python -m pytest tests/test_streaming_rules.py::test_temporal_rule_requires_paired_observations -q --basetemp=C:/sfpt-temporal-t3", exit: 0}
  - id: T4
    status: done
    red: {command: "python -m pytest tests/test_analyze_streaming_composition.py::test_temporal_cli_and_mcp_envelopes_match -q --basetemp=C:/sfpt-temporal-t4-red", exit: 1}
    green: {command: "python -m pytest tests/test_analyze_streaming_composition.py::test_temporal_cli_and_mcp_envelopes_match -q --basetemp=C:/sfpt-temporal-t4", exit: 0}
  - id: T5
    status: done
    red: {command: "python -m pytest tests/test_fixtures_golden_streaming_temporal.py::test_fixture_goldens -q --basetemp=C:/sfpt-temporal-t5-red", exit: 1}
    green: {command: "python -m pytest tests/test_fixtures_golden_streaming_temporal.py tests/test_fixtures_kind_coverage.py -q --basetemp=C:/sfpt-temporal-goldens", exit: 0}
  - id: T6
    status: done
    red: {command: "python -m pytest tests/test_reference_docs.py::test_referencia_em_dia tests/test_reference_docs.py::test_toda_tool_e_skill_tem_pagina tests/test_docs_coverage.py -q --basetemp=C:/sfpt-temporal-docs", exit: 1}
    green: {command: "python -m pytest tests/test_reference_docs.py -q --basetemp=C:/sfpt-temporal-reference", exit: 0}
claims:
  - text: "O compositor temporal aceita identidade de query e transporte, tolerância declarada, timestamps observados e emite pares com skew, source_fact_ids e causal_inference=false; ausência de dados permanece unresolved."
    evidence_ref: "tests/test_facts_streaming_temporal.py"
  - text: "Kafka e Kinesis preservam timestamp/observed_at já observado no artefato, sem relógio local ou ordem de arquivo."
    evidence_ref: "tests/test_facts_transport.py::test_transport_preserves_observed_timestamp"
  - text: "SF-STREAMOBS-002 só dispara com dois pares temporais completos, processamento abaixo da entrada e backlog observado; não usa limiar fixo de lag, custo ou ganho."
    evidence_ref: "rules/catalog/streaming_observability.yaml; tests/test_streaming_rules.py::test_temporal_rule_requires_paired_observations"
  - text: "Fixtures Kafka, Kinesis e missing_timestamp persistem facts/findings esperados; o corpus cobre streaming.temporal.diagnostic e streaming.temporal.unresolved."
    evidence_ref: "fixtures/streaming_temporal/*/expected; tests/test_fixtures_kind_coverage.py"
  - text: "CLI e MCP expõem mode=temporal e max_skew_seconds com envelope comum e sem operação de escrita."
    evidence_ref: "tests/test_analyze_streaming_composition.py::test_temporal_cli_and_mcp_envelopes_match"
  - text: "Skill, mirrors, knowledge, prompt coverage, referências geradas, surface lock, offline manifest e números correntes estão sincronizados."
    evidence_ref: "scripts/sync_skills.py --check; scripts/gen_reference_docs.py --check; scripts/check_surface_lock.py; scripts/verify_offline_bundle.py --check; scripts/check_status_numbers.py --strict"
  - text: "Gates de regra, runtime, docs, corpus e wheel passaram: 1188 testes de catálogo/docs/knowledge; 766 testes de runtime-scope; 66 testes de goldens/coverage; 46 testes de wheel."
    evidence_ref: "commands recorded in this report and ship.md"
change_id: null
---

# STREAMING_TEMPORAL_EVIDENCE — relatório do build

## Resultado

Build concluído em T1–T6. A implementação permanece offline e determinística:
ela compõe facts já extraídos, não consulta Spark, Kafka, Kinesis, CloudWatch ou
qualquer provider. O resumo temporal carrega ids de origem para expansão posterior
sem copiar todos os facts para o envelope compacto.

## Desvios e decisões durante o build

- **T5.** O primeiro runner verificava apenas contrato em `meta.yaml`; o gate
  `test_fixtures_kind_coverage` exigiu goldens persistidos em `expected/`. Foram
  adicionados `facts.json` e `findings.json` para Kafka, Kinesis e
  `missing_timestamp`, incluindo o finding positivo de `SF-STREAMOBS-002`.
- **T6.** A primeira rodada documental acusou `rule_count` antigo (208 contra
  209). Manifest, README, guias e STATUS foram atualizados; `check_status_numbers`
  terminou com zero divergências.
- **Ambiente.** O pytest padrão encontrou permissão negada no diretório temporário
  global do Windows; os comandos foram repetidos com `--basetemp=C:/sfpt-*`.
- **Escopo solicitado.** A suíte completa não foi executada nesta fase. Os gates
  direcionados acima são o conjunto proporcional às mudanças desta feature.

## Revisão por tarefa

- **T1–T2:** timestamps são aceitos somente quando observados e normalizáveis;
  timestamp numérico exige unidade explícita quando necessário. Timestamp ausente
  não vira relógio local.
- **T3:** o finding preserva evidência factual, `runtime_scope: {}`, ação de
  baseline e rollback; não estima custo, SLO, throughput ou causa raiz.
- **T4:** CLI e MCP chamam o mesmo core e recebem o mesmo envelope; `summary`
  mantém apenas agregados e `source_fact_ids` necessários para reauditoria.
- **T5:** positivos têm duas observações pareadas para Kafka e Kinesis; o caso
  sem timestamp produz `streaming.temporal.unresolved` e nenhum finding.
- **T6:** referências geradas e mirrors foram regenerados, não editados em
  paralelo; o hash do knowledge alterado foi atualizado no manifest offline.

## Medida

Não há alegação de ganho de performance, custo ou qualidade funcional. A medida
entregue é de cobertura e contrato: pares observados, skew declarado, evidência
ancorada e recusa nomeada quando a janela não pode ser comparada.
