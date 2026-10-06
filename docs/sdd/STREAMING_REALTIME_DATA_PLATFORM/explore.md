---
sdd: 1
feature: STREAMING_REALTIME_DATA_PLATFORM
phase: explore
profile: dev
status: ready
approaches:
  - id: A
    summary: "Construir primeiro um backbone evidence-first: contratos de artefato, facts e runtime guards para Structured Streaming, depois transportar o mesmo modelo para Kafka/MSK, Kinesis, Flink, Glue RTM, CDC, contratos e Iceberg em ondas independentes."
    tradeoffs:
      - "Entrega menos nomes visíveis no primeiro ciclo, mas cada capacidade nova já é extraível, versionada, julgável, roteável e testável."
      - "Exige mais desenho inicial de schemas, unresolved e matrizes de versão."
      - "Permite agentes e skills especializados somente depois de existir domínio observável para eles consumirem."
  - id: B
    summary: "Criar primeiro um envelope universal de artefatos e registries para todos os transportes e engines, deixando as rules específicas para ciclos posteriores."
    tradeoffs:
      - "Aumenta rapidamente a cobertura de ingestão e inventário."
      - "Cria uma superfície grande de collectors, CLI e MCP antes de haver diagnóstico comprovado."
      - "Pode produzir muitos facts genéricos sem findings acionáveis e adia os guards de runtime que o prompt considera críticos."
  - id: C
    summary: "Priorizar knowledge packs, skills, coordinators e exemplos end-to-end, reutilizando os especialistas streaming existentes, e internalizar evidence depois."
    tradeoffs:
      - "Melhora rapidamente a experiência textual e o roteamento aparente."
      - "Mantém os thresholds hard-coded atuais e não satisfaz o critério de domínio artefato → extractor → Fact → rule."
      - "Risco alto de recomendações sem fact_id, sem runtime guard e sem validação determinística."
chosen: A
---

# STREAMING_REALTIME_DATA_PLATFORM — exploração

## Origem e propósito

O pedido é executar `prompt_evo_streaming.md` e elevar o SparkForge para batch,
streaming, near-real-time, real-time, CDC e arquiteturas event-driven. O prompt
define escopo amplo demais para uma única alteração atômica; esta exploração
define o primeiro backbone e registra as ondas seguintes, cada uma com ciclo SDD
próprio quando criar regras, collectors ou superfície pública.

Perfil: `dev`; a mudança é no próprio SparkForge.

## Baseline observado

- Branch `main`, commit inicial `a540c7805da0c79bbd71b6ed741f0ec3875e9b2f`.
- `sparkforge-aws doctor --repo .`: pacote ok (`sparkforge-aws 0.5.0`, Python `3.14.6`), MCP montável com `115 tools`, catálogo com `177 regras`; boto3 ausente, fontes de knowledge com drift e integrações de usuário não configuradas.
- Índice de código sincronizado em `.sparkforge/local/codeintel/graph.sqlite3`: `1.391` arquivos, `14.851` nós, `23.645` edges, `33.137` unresolved; busca por `streaming` retornou somente testes de Lake Formation e busca por `kafka` somente `tests/test_database_specialists.py`.
- Fact modules: `52`; skills canônicas com `SKILL.md`: `52`; agents coordenadores: `12`; executors: `5`; knowledge packs: `18` diretórios.
- O primeiro `python -m pytest -q` foi bloqueado antes dos testes pela permissão de `C:\Users\edgar\AppData\Local\Temp\pytest-of-edgar`. Uma segunda execução com `--basetemp=.pytest-baseline` foi iniciada para separar limitação ambiental de regressões; o diretório de baseline não pertence à feature.

## Matriz de gap inicial

Classificação: `knowledge-only`, `workflow-only`, `artifact-aware`,
`fact-aware`, `rule-aware`, `diagnosable`, `composable`, `production-grade`.
Uma menção em Markdown não conta como capacidade implementada.

| Capability | existe | parcial | ausente | evidência atual | nível inicial |
|---|---:|---:|---:|---|---|
| Structured Streaming |  | x |  | `knowledge/streaming-reliability.md`; nenhum analyzer de progress/source | knowledge-only |
| Spark Real-Time |  |  | x | nenhum runtime matrix, extractor ou rule específico | ausente |
| Kafka |  | x |  | `sparkforge_aws/streaming/kafka.py` e teste unitário, sem artifact/facts/rules | workflow-only |
| MSK |  | x |  | mesmo especialista genérico de Kafka; sem dump de cluster/versão | workflow-only |
| Kafka Connect |  |  | x | nenhum artifact contract, collector ou analyzer | ausente |
| Kafka Streams |  |  | x | nenhum model/runtime knowledge específico | ausente |
| Kinesis |  | x |  | `sparkforge_aws/streaming/kinesis.py` e teste unitário, sem facts/rules | workflow-only |
| Flink | x |  |  | só referência resumida em `knowledge/streaming-reliability.md` | knowledge-only |
| Managed Flink | x |  |  | skill AWS geral cita serviço, sem artifact/runtime guard | knowledge-only |
| Glue Streaming / RTM |  | x |  | regras existentes cobrem Lake Formation e docs Glue, não análise streaming | knowledge-only |
| CDC / DMS / Debezium |  |  | x | nenhum extractor, fixture ou rule dedicada | ausente |
| Schema Registry / data contracts | x |  |  | `knowledge/data-contracts-schema-evolution.md`, sem facts/rules | knowledge-only |
| Streaming Iceberg | x |  |  | knowledge Iceberg existe, sem correlação progress → commit/snapshot | knowledge-only |
| Event-driven architecture | x |  |  | skills AWS e Step Functions existentes, sem modelo streaming | workflow-only |
| Streaming observability |  |  | x | sem analyzer de `StreamingQueryProgress`, lag/time-series/state | ausente |
| Streaming FinOps |  |  | x | finops atual não recebe throughput/lag/state/checkpoint streaming | ausente |
| Streaming security |  | x |  | IAM/Lake Formation genéricos; sem TLS/SASL/MSK/Kinesis artifacts | knowledge-only |
| Real-time analytics |  | x |  | Athena/serving existentes, sem requisitos de freshness/latency | workflow-only |
| Architecture decision support |  | x |  | Decision Plane existe, sem declared streaming requirements/candidate checks | composable parcial |

## O que entra no backbone inicial

1. Modelo comum de streaming separado em transport/log, processing e sink/serving.
2. Artefato de código Structured Streaming com facts para `readStream`, source,
   `writeStream`, sink, checkpoint, trigger, output mode, watermark, windows,
   joins, deduplication, `foreachBatch`, stateful operations e options visíveis.
3. Artefato de `StreamingQueryProgress` como série temporal, com fatos por batch,
   source/sink/state/event-time e `unresolved` quando uma amostra não sustenta
   tendência.
4. Runtime context declarativo/observado para separar Spark upstream de Glue RTM,
   incluindo capability guard; nenhuma API nova será aplicada fora do runtime
   confirmado.
5. Primeiro conjunto de rules sem limiar universal inventado: backlog crescente,
   processing sustentadamente abaixo de input, trigger incompatível com duração do
   batch, state sem retenção observável, watermark parado e checkpoint ausente,
   sempre com evidência suficiente e fonte versionada.
6. Fixtures positivas, negativas, unresolved e runtime-divergent; CLI/MCP somente
   depois do contrato interno e do surface lock.

## Ondas posteriores registradas

- `STREAMING_TRANSPORT_DIAGNOSTICS`: Kafka, MSK, Kinesis, Connect e métricas por
  partição/shard/grupo, sem threshold hard-coded.
- `STREAMING_PROCESSING_RUNTIMES`: Flink, Managed Flink, Glue Streaming e RTM,
  com matrizes upstream versus serviço gerenciado.
- `STREAMING_CDC_CONTRACTS`: DMS, Debezium, tombstones, ordering, transaction
  boundaries, Schema Registry e compatibilidade de producer/consumer.
- `STREAMING_LAKEHOUSE_OBSERVABILITY`: correlação progress/checkpoint com Iceberg,
  commit frequency, files/manifests/snapshots e serving.
- `STREAMING_ARCHITECTURE_DECISIONS`: requisitos declarados, candidatos, violações,
  custo/ops unresolved, ADR e routing para especialistas.
- `STREAMING_AGENTIC_SURFACE`: skills, coordinators, mirrors e MCP apenas quando
  as ondas anteriores tiverem facts/rules/fixtures; nenhum agent será prova de
  domínio por si só.

## Pergunta para fechar explore

1. Qual abordagem deve governar a primeira onda? Resposta: `A`, backbone
   evidence-first, conforme o pedido original de executar a evolução completa e a
   recomendação registrada nesta exploração.

## Escolha

`A`, porque é a única que preserva o contrato do repositório e permite expandir para
todas as capacidades do prompt sem transformar menções de streaming em diagnósticos
sem evidência.
