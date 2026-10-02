---
sdd: 1
feature: STREAMING_CDC
phase: explore
profile: dev
status: ready
approaches:
  - id: A
    summary: "Um extrator offline com três vocabulários explícitos: CDC, Debezium e DMS."
    tradeoffs:
      - "reaproveita envelope, fixtures e superfície"
      - "não substitui collectors live nem matriz de versões"
  - id: B
    summary: "Um extrator independente por produto."
    tradeoffs:
      - "isolamento maior"
      - "duplicação de contratos, testes e ferramentas"
chosen: A
---

# STREAMING_CDC — exploração

## Problema

O prompt exige CDC real para projetos streaming e batch, incluindo Debezium,
Kafka Connect e AWS DMS. O repositório precisa distinguir evento observado,
configuração do conector e task de replicação, sem concluir idempotência,
exactly-once ou ausência de perda por nome de produto.

## Escopo desta wave

Extrair dumps JSON/JSONL locais de eventos CDC, configuração/status Debezium e
task/endpoints/mappings/estatísticas DMS; publicar regras com evidência,
fixtures positivas/negativas/unresolved, CLI/MCP, skill, agente e routing.
Collectors live, matriz de runtime, schema registry e validação funcional ficam
nomeados para waves seguintes.

## Perguntas respondidas

1. O analyzer acessa banco, broker ou AWS? Não; lê somente dumps versionados.
2. Posição, chave e snapshot/CDC seam ausentes são zero? Não; viram unresolved.
3. CDC, Debezium e DMS compartilham namespace? Não; o envelope é comum, os
   vocabulários são separados.
