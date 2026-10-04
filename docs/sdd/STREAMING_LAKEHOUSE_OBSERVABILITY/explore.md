---
sdd: 1
feature: STREAMING_LAKEHOUSE_OBSERVABILITY
phase: explore
profile: dev
status: ready
approaches:
  - id: A
    summary: "Composição offline explícita sobre facts de progresso, transporte e Iceberg, com vínculo declarado pelo operador."
    tradeoffs:
      - "preserva a separação entre extração e composição"
      - "exige declarar query, tabela e grupo para impedir correlação por conveniência"
  - id: B
    summary: "Inferir vínculos por nomes de arquivo, descrição de sink e proximidade temporal."
    tradeoffs:
      - "menos parâmetros de entrada"
      - "pode atribuir lag, commits e estado ao workload errado"
chosen: A
---

# STREAMING_LAKEHOUSE_OBSERVABILITY — exploração

## Problema

O prompt exige diagnóstico de streaming + Iceberg e observabilidade sem
confundir correlação com causalidade. O repositório já extrai progresso,
transporte e metadata Iceberg separadamente, mas não existe um fato composto
que carregue as três procedências e exponha os pontos cegos.

## Escopo desta wave

Criar composição offline de facts já extraídos para dois caminhos: vínculo
Structured Streaming→Iceberg e vínculo progresso→lag/iterator age. A composição
exige nomes declarados e correspondência observada; ausência, ambiguidade ou
operação não-append permanecem explícitas. Não haverá collector live, custo,
SLO inventado ou afirmação causal.

## Perguntas respondidas

1. O correlator consulta AWS, Kafka ou Iceberg? Não; lê apenas arquivos de facts.
2. Uma amostra de lag prova causa do atraso? Não; produz evidência correlata e
   deixa a causa para investigação posterior.
3. Um commit Iceberg por observação é automaticamente ruim? Não; a saída mede
   a relação e só regras com evidência de operação não-append podem disparar.
