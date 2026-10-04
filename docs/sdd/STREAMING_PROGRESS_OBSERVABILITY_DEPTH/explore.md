---
sdd: 1
feature: STREAMING_PROGRESS_OBSERVABILITY_DEPTH
phase: explore
profile: dev
status: ready
approaches:
  - id: A
    summary: "Ampliar streaming.progress.series com resumos temporais determinísticos de duração, memória do state e watermark, mantendo o extrator existente."
    tradeoffs:
      - "entrega evidência compacta e reutiliza regras, fixtures e fluxo atual"
      - "não substitui coleta live, replay ou diagnóstico causal"
  - id: B
    summary: "Criar um analyzer separado para observabilidade temporal de progress."
    tradeoffs:
      - "poderia evoluir independente do extrator"
      - "duplicaria parsing de StreamingQueryProgress e aumentaria superfície"
  - id: C
    summary: "Derivar watermark e memória somente no compositor de SLO."
    tradeoffs:
      - "não mudaria o extrator"
      - "perderia fatos reutilizáveis e misturaria extração com julgamento"
chosen: A
---

# STREAMING_PROGRESS_OBSERVABILITY_DEPTH — exploração

## Evidência que abriu a frente

`sparkforge/facts/streaming.py` já extrai `streaming.progress.batch`,
`streaming.progress.event_time` e `streaming.progress.state_operator`, mas o
fact `streaming.progress.series` resume apenas taxas e total de linhas do state.
Assim, a evidência já presente não chega compactada ao judge para duração,
memória do state ou avanço de watermark.

## Perguntas feitas, uma por vez

1. A saída deve declarar causa, freshness ou exactly-once? Não. Deve publicar
   somente medidas e sintomas observados.
2. Um watermark ausente pode ser tratado como zero ou avanço desconhecido? Não;
   o extractor deve preservar a lacuna como unresolved quando a série começou a
   declarar watermark, mas não permite resumi-la.
3. O estado pode ser resumido como uma única métrica? Somente como soma
   observada entre operadores, preservando a ausência de métrica quando algum
   operador não fornece valor.

## Escolha

A. Ampliar o fact de série com timestamp span, duração de batch, memória do
state e watermark; adicionar regras evidence-first para watermark parado e
crescimento de memória. Não haverá threshold inventado, p95, freshness,
causalidade, custo ou chamada live.
