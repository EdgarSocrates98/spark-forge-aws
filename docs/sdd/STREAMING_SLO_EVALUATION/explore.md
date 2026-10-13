---
sdd: 1
feature: STREAMING_SLO_EVALUATION
phase: explore
profile: dev
status: ready
approaches:
  - id: A
    summary: "Compor uma avaliação SLO offline sobre facts declarados e batches Structured Streaming já extraídos, usando o modo streaming-composition existente."
    tradeoffs:
      - "mantém facts, composição e judge separados e reutiliza CLI/MCP"
      - "a primeira versão fica limitada a métricas diretamente observadas no progress JSONL"
  - id: B
    summary: "Criar collector live de CloudWatch, Spark ou Kafka para preencher a janela SLO automaticamente."
    tradeoffs:
      - "poderia observar séries operacionais sem preparação manual"
      - "introduz rede, credencial, custo e autorização fora do core offline"
  - id: C
    summary: "Transformar streaming.slo em finding diretamente no extractor de contrato."
    tradeoffs:
      - "menos código de composição"
      - "mistura declaração com observação e permite afirmar atendimento sem métrica"
chosen: A
---

# STREAMING_SLO_EVALUATION — exploração

## Perfil

`dev`: evolução do SparkForge, sem acessar AWS ou serviços streaming live.

## Perguntas feitas

1. Qual gap P0 permanece? `analyze streaming-ops` já preserva target, operador,
   unidade, janela e fonte, mas mede somente declaração; nenhum verbo compara a
   declaração com uma série observada.
2. Qual evidência precisa ser reauditável? O nome da query e do SLO, métrica,
   operador, target, unidade, janela coberta, valores observados e ids dos facts
   `streaming.slo`/`streaming.progress.batch`.
3. O que fica fora? Collector live, inferência de p95/freshness, atribuição de
   causa, custo, disponibilidade e qualquer sucesso sem janela observada.

## Escolha

A. Ela fecha a lacuna usando artefatos já coletados, exige identidade declarada,
recusa métrica/unidade/janela incompatível e deixa transportes sem timestamp como
`unresolved`, preservando o contrato offline.
