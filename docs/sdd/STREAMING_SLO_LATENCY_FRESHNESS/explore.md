---
sdd: 1
feature: STREAMING_SLO_LATENCY_FRESHNESS
phase: explore
profile: dev
status: ready
approaches:
  - id: A
    summary: "Estender o compositor streaming.slo com statistic=p95 e métricas de latência/freshness observadas no progress."
    tradeoffs:
      - "reutiliza CLI/MCP, envelope, regras e identidade existentes"
      - "continua offline e não substitui série live, endpoint ou validação funcional"
  - id: B
    summary: "Criar analyzer separado para latência e freshness."
    tradeoffs:
      - "separaria o vocabulário"
      - "duplicaria seleção de query, janela, unidade, identidade e proveniência"
  - id: C
    summary: "Aceitar nomes p95/freshness no contrato sem calcular observações."
    tradeoffs:
      - "mudança pequena"
      - "não entrega o SLI pedido e aumentaria falsa sensação de cobertura"
chosen: A
---

# STREAMING_SLO_LATENCY_FRESHNESS — exploração

## Evidência que abriu a frente

`sparkforge_aws/facts/streaming_slo.py` já avalia séries timestampadas de progress,
sink, Kafka e Kinesis, mas só compara cada valor individual. O contrato de
streaming cita p95 end-to-end latency e freshness como SLOs relevantes, porém
`streaming.progress.batch` ainda não publica uma métrica de freshness derivada
de `timestamp` e `eventTime.max`, e nenhuma avaliação calcula percentil.

## Perguntas feitas, uma por vez

1. Freshness pode ser inferida de qualquer campo de event time? Não. Somente
   `eventTime.max` timezone-aware pareado ao timestamp da mesma observação, ou
   uma medida explícita `freshnessMs`, pode produzir a métrica.
2. `timestamp - eventTime.max` prova end-to-end latency? Não. O nome emitido é
   `freshness_ms`; end-to-end latency exige medida explícita no progress.
3. O p95 deve interpolar valores? Não. O contrato usa nearest-rank
   determinístico (`ceil(0.95 * n)`), preservando amostra e limites.
4. Ausência parcial da métrica pode ser ignorada? Não. A série SLO permanece
   unresolved se qualquer observação selecionada não tiver valor ou timestamp.

## Escolha

A. Adicionar `statistic: p95` opcional à declaração SLO, métricas observáveis
`freshness_ms` e `end_to_end_latency_ms`, cálculo nearest-rank e goldens. A
frente não cria regra de causa, threshold, collector live, benchmark ou claim
de exatamente-once.
