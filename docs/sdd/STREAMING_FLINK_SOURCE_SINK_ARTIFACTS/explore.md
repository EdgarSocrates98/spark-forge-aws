---
sdd: 1
feature: STREAMING_FLINK_SOURCE_SINK_ARTIFACTS
phase: explore
profile: dev
status: ready
approaches:
  - id: A
    summary: "Estender o extrator Flink existente para emitir facts explícitos de source e sink, preservando métricas presentes e unresolved quando ausentes."
    tradeoffs:
      - "Reutiliza analyzer, judge, fixtures e surface atuais; não cria nova operação."
      - "Exige regenerar goldens existentes porque a ausência de source/sink passa a ser observável."
  - id: B
    summary: "Criar um extrator separado para dumps de conectores Flink."
    tradeoffs:
      - "Separaria o artefato de conectores."
      - "Duplicaria parsing, registro de kinds e contrato de fixture sem evidência de um formato distinto."
  - id: C
    summary: "Derivar source/sink somente de flink.operator pelo campo type."
    tradeoffs:
      - "Nenhum novo parsing."
      - "Não preserva métricas específicas de connector, backlog, lag ou commit e confundiria observação indireta com artefato explícito."
chosen: A
---

# STREAMING_FLINK_SOURCE_SINK_ARTIFACTS — exploração

## Perfil e motivo

`dev`: mudança no SparkForge. A cobertura de `prompt_evo_streaming.md` já tinha
facts determinísticos para job, operator, checkpoint e state do Apache Flink,
mas source e sink só apareciam, quando muito, como operators. Isso impede
preservar métricas específicas de entrada e saída e impede declarar o blind
spot quando o dump não as traz.

## Evidência consultada

- `sparkforge/facts/flink.py`: `EMITTED_KINDS` não inclui source/sink e o
  extrator só lê `operators`, `checkpoints` e `state` no namespace Apache.
- `tests/test_facts_flink.py` e `fixtures/flink/`: corpus cobre os kinds atuais,
  mas não tem contrato explícito para source/sink.
- `skills/analyze-flink-job/SKILL.md`: exige separar Apache Flink de Managed
  Flink e correlacionar source/sink com throughput, backlog e checkpoint sem
  inferir sem evidência.
- `docs/streaming/prompt-coverage.md`: source/sink continuam lacuna declarada
  na linha de Flink.

## Escolha

Escolhida A. O formato atual já aceita dumps de job com listas nomeadas e o
mesmo provenance basta para facts de source/sink. B não tem artefato distinto
demonstrado; C perde informação e transforma uma indicação do operador em
identidade de source/sink.

## Limites

Esta wave não consulta Flink ou AWS, não classifica connector por conhecimento
externo, não transforma `num_records_*` em throughput temporal, não conclui
exactly-once e não diagnostica causa raiz a partir de uma métrica isolada.
