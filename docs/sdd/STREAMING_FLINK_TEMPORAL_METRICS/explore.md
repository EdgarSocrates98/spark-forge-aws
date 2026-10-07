---
sdd: 1
feature: STREAMING_FLINK_TEMPORAL_METRICS
phase: explore
profile: dev
status: ready
approaches:
  - id: A
    summary: "Ampliar o extrator offline existente para aceitar pontos temporais upstream e emitir flink.metric, sem nova porta."
    tradeoffs:
      - "reutiliza analyze flink, facts, goldens e skill existentes"
      - "não resolve aquisição live nem métricas específicas de cada deployment"
  - id: B
    summary: "Criar collector Flink REST e uma nova tool para buscar métricas em runtime."
    tradeoffs:
      - "cobre aquisição live quando endpoint e credencial existem"
      - "aumenta surface, dependência de endpoint, segurança e custo de contexto"
  - id: C
    summary: "Adicionar uma regra que trate backpressure/operator facts atuais como série temporal."
    tradeoffs:
      - "parece menor no catálogo"
      - "mistura observação pontual com julgamento e inventa tempo ausente"
chosen: A
---

# STREAMING_FLINK_TEMPORAL_METRICS — exploração

## Perfil

`dev`: a mudança é no próprio SparkForge. O pedido do objetivo maior já fixa a
restrição evidence-first: ampliar conhecimento e utilidade sem inferir runtime,
saúde ou economia.

## Evidência consultada

- `sparkforge-aws sdd status --repo .`: Wave D tem Flink offline e Managed Flink
  temporal bounded entregue; upstream temporal genérico continua gap.
- `sparkforge-aws code search`/leitura de `sparkforge_aws/facts/flink.py`: o extrator
  upstream não emite `flink.metric`; Managed Flink já emite
  `managed_flink.metric` em namespace separado.
- `docs/streaming/prompt-coverage.md` e `knowledge/flink-streaming.md`:
  collector/live, savepoints e métricas temporais upstream permanecem fora.

## Escolha

A é escolhida para fechar o contrato offline mínimo verificável sem afirmar que
um dump é um runtime vivo. B fica para feature própria quando houver endpoint,
credencial e contrato de coleta. C é rejeitada porque um único ponto de
backpressure não é série temporal.
