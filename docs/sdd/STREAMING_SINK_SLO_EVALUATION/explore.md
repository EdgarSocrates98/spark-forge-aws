---
sdd: 1
feature: STREAMING_SINK_SLO_EVALUATION
phase: explore
profile: dev
status: ready
approaches:
  - id: A
    summary: "Estender mode=slo para avaliar num_output_rows em streaming.progress.sink, ligando batch_id ao timestamp/query do batch já extraído."
    tradeoffs:
      - "reutiliza CLI/MCP, contrato SLO e regras existentes"
      - "avalia throughput de saída observado, não freshness, p95 ou exactly-once"
  - id: B
    summary: "Criar um extractor novo de métricas de sink com identidade e relógio próprios."
    tradeoffs:
      - "poderia carregar mais contexto de sink"
      - "duplicaria o contrato StreamingQueryProgress e quebraria a separação extractor/compositor"
  - id: C
    summary: "Usar somente streaming.ops e o compositor genérico de observabilidade."
    tradeoffs:
      - "evitaria mudança no SLO streaming"
      - "não ligaria num_output_rows observado à janela da query"
chosen: A
---

# STREAMING_SINK_SLO_EVALUATION — exploração

## Evidência que abriu a frente

`streaming.progress.sink` já é extraído de `StreamingQueryProgress` com
`batch_id` e `num_output_rows`. O mesmo registro produz
`streaming.progress.batch` com `query_name` e timestamp. O comparador SLO já
exige declaração, unidade, identidade, observações e cobertura temporal; falta
apenas aceitar a métrica direta de saída e fazer o vínculo por arquivo e batch.

## Perguntas feitas, uma por vez

1. A métrica representa freshness ou exactly-once? Não. Ela representa somente
   quantidade de linhas emitidas pelo sink no batch observado.
2. O timestamp pode ser inventado a partir da ordem do sink? Não. Ele deve vir
   do batch correspondente; sem correspondência, o resultado é unresolved.
3. Como separar múltiplos sinks? A declaração pode informar `sink_name`; sem
   nome e com descrições distintas, a composição recusa ambiguidade.

## Escolha

A. Reutilizar `mode=slo`, `streaming.slo.evaluation` e as regras existentes.
Adicionar apenas aliases canônicos para `num_output_rows`, fonte
`streaming_sink` e vínculo determinístico com o batch. Nenhum threshold,
freshness, quantil, causa, custo ou garantia de entrega será inferido.
