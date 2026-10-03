---
sdd: 1
feature: STREAMING_GLUE_SOURCE_SINK_ARTIFACTS
phase: explore
profile: dev
status: ready
approaches:
  - id: A
    summary: "Estender o extrator Glue Streaming existente para facts explícitos de source e sink, preservando observações escalares e unresolved."
    tradeoffs:
      - "Reutiliza analyzer, surface, judge e corpus existentes; não cria segundo modelo Glue."
      - "Goldens existentes precisam registrar a nova ausência ou os endpoints declarados."
  - id: B
    summary: "Criar extrator separado para conectores Glue."
    tradeoffs:
      - "Separaria endpoints do job."
      - "Não há artefato produtor distinto demonstrado e duplicaria o contrato Glue."
  - id: C
    summary: "Derivar source/sink somente de source_type e output_mode do job."
    tradeoffs:
      - "Seria barato."
      - "Confundiria configuração agregada com identidade e métricas do endpoint."
chosen: A
---

# STREAMING_GLUE_SOURCE_SINK_ARTIFACTS — exploração

## Perfil e motivo

`dev`: mudança no SparkForge. O extrator Glue Streaming já preserva modo,
runtime, source type agregado, output e capacidade declarada, mas não separa
endpoints. Isso impede correlacionar fonte/sink com métricas observadas e torna
silenciosa a ausência de evidência específica.

## Evidência consultada

- `sparkforge/facts/glue_streaming.py`: o contrato atual emite `glue.streaming.job`,
  `glue.streaming.runtime`, `glue.streaming.analyzed` e `glue.streaming.unresolved`;
  `source_type` fica no job.
- `fixtures/glue_streaming/`: o corpus cobre RTM válido, capacidade ausente e
  incompatibilidade, mas não possui facts independentes de endpoint.
- `skills/review-glue-streaming/SKILL.md` e `knowledge/glue-streaming-rtm.md`:
  exigem preservar lacunas e não chamar AWS no analyzer offline.
- `docs/streaming/prompt-coverage.md`: Glue Streaming ainda lista source/sink
  como lacuna parcial.

## Escolha

Escolhida A. O bloco `stream` já é o artefato observado e pode receber
`sources`/`source` e `sinks`/`sink`. B não tem formato distinto demonstrado; C
perde identidade, connector e medidas e transforma declaração agregada em
observação de endpoint.

## Limites

Esta wave não consulta Glue, Kafka, Kinesis ou CloudWatch, não infere endpoint a
partir de `source_type`, não calcula throughput/latência/capacidade e não
conclui exatamente-once ou correção funcional.
