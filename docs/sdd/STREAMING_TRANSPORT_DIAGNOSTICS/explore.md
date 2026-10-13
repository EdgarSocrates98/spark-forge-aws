---
sdd: 1
feature: STREAMING_TRANSPORT_DIAGNOSTICS
phase: explore
profile: dev
status: ready
approaches:
  - id: A
    summary: "Contrato único analyze transport com especializações Kafka, MSK e Kinesis."
    tradeoffs:
      - "um envelope comum para CLI e MCP"
      - "parser precisa preservar diferenças específicas por domínio"
  - id: B
    summary: "Um verbo independente por serviço de transporte."
    tradeoffs:
      - "isolamento por serviço"
      - "triplica superfície e fixtures sem ganho medido nesta onda"
chosen: A
---

# STREAMING_TRANSPORT_DIAGNOSTICS — exploração

## Problema

O backbone Structured Streaming já preserva progresso da query, mas não lê os
artefatos que explicam o transporte. Sem dump de topic/partition/group/lag ou
stream/shard/iterator age, o agente não consegue distinguir um gargalo de
processamento de um atraso no transporte. O prompt exige diagnósticos offline,
com collectors read-only separados, sem transformar a existência de mensagens
em alegação de hot partition.

## Opções

- **A — contrato único `analyze transport` com especializações explícitas.** Um
  parser JSON/JSONL comum preserva `artifact: kafka|msk|kinesis`, emite facts
  específicos por domínio e mantém `unresolved` quando a forma não responde.
  CLI/MCP usam o mesmo envelope.
- **B — um verbo e módulo independente para cada serviço.** Maior isolamento,
  mas triplica envelope, fixtures e surface sem benefício medido nesta onda.

Escolha: **A**.

## Matriz de lacunas

| superfície | hoje | alvo desta onda | fora desta onda |
|---|---|---|---|
| Kafka topic/partition/group/lag | código de workflow sem artifact contract | facts offline de dump salvo | collector Kafka live |
| MSK cluster/version/security | knowledge genérico | facts de cluster e limites de evidência | matriz completa de versões e rede |
| Kinesis stream/shard/metrics | código de workflow sem analyzer | facts offline de shard e métrica | collector/CloudWatch live |
| regras | nenhuma regra de transporte | nenhum finding sem baseline operacional | rules e correlação com progress |
| agentes/skills | coordenador genérico | knowledge e rota existentes permanecem | especialista dedicado |

## Artefatos mínimos

- JSON/JSONL de `kafka-consumer-groups --describe`, `kafka-topics --describe`,
  configs e dump de cluster;
- JSON salvo de `describe-cluster` MSK, com versão/broker/security quando
  observados;
- JSON salvo de stream/shards/metrics Kinesis;
- fixture positiva, negativa e unresolved para cada família.

## Lacunas nomeadas

- U1: não há API Kafka/CloudWatch live nesta onda;
- U2: sem timestamp comum não há série de lag nem tendência;
- U3: um dump sem distribuição por partition/shard não prova hot partition;
- U4: versão declarada sem dump do serviço não prova compatibilidade MSK.

## Próximo passo

Definir parser e envelope, com fatos de observação e nenhum threshold inventado.
