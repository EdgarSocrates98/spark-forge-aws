---
sdd: 1
feature: STREAMING_TEMPORAL_EVIDENCE
phase: explore
profile: dev
status: ready
approaches:
  - id: A
    summary: "Adicionar composição temporal offline ao analyzer existente, com timestamp, identidade e tolerância declarados."
    tradeoffs:
      - "reusa facts, CLI, MCP e envelope existentes"
      - "exige evidência temporal suficiente e altera o surface lock"
  - id: B
    summary: "Criar collector live para métricas de broker, CloudWatch e query progress."
    tradeoffs:
      - "aproxima a operação de produção"
      - "exige credenciais, endpoints, relógios e contratos externos não presentes no core offline"
chosen: A
---

# STREAMING_TEMPORAL_EVIDENCE — exploração

## Problema

O repositório já compõe progresso Structured Streaming com uma medida pontual
de Kafka/Kinesis. Isso não responde se as observações pertencem à mesma janela
nem preserva uma série pareada de longa duração. A lacuna impede separar
evidência temporal de uma coincidência de snapshots.

## Escopo desta wave

Adicionar um modo temporal ao compositor existente. O modo recebe facts já
extraídos, exige `query_name`, `transport_key` e `max_skew_seconds` declarados,
normaliza timestamps observados, cria pares determinísticos dentro da janela e
carrega os ids de origem. Sem timestamps, identidade, duas observações ou par
válido, emite `streaming.temporal.unresolved`; não preenche zero, não escolhe
causa e não chama Spark, Kafka, Kinesis, CloudWatch ou provider.

O transporte preservará timestamps numéricos já fornecidos no dump Kafka/Kinesis;
progresso continua usando o timestamp ISO observado em cada batch. Nenhum relógio
é inferido a partir da ordem dos arquivos.

## Perguntas respondidas

1. Existe uma janela temporal declarada que pareie progresso e transporte? Sim,
   apenas quando os timestamps observados respeitam `max_skew_seconds`.
2. A janela prova que backlog causou atraso? Não; o fato registra coexistência
   pareada e mantém `causal_inference: false`.
3. Uma ausência de timestamp prova que não houve backlog? Não; vira unresolved
   com o campo que destravaria a análise.
