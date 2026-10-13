# Receita — avaliar um pipeline streaming

**O quê:** `analyze streaming` + `analyze transport` + `analyze
streaming-composition` extraem facts de fonte Structured Streaming, progress,
checkpoint e dumps Kafka/MSK/Kinesis/Flink — `judge` aplica as áreas
`streaming*` do catálogo.
**Por que:** diagnóstico streaming sem rodar o job — separa declaração
estática (source/sink/checkpoint) de medida temporal (progress, lag, iterator
age) e de resultado funcional.
**Quando:** avaliar um job Glue Streaming/Structured Streaming/Managed Flink
pelo que ele deixou em artefato.
**Quando não:** prova de exactly-once, capacidade ou saúde end-to-end — o que
não está no artefato sai `unresolved`, nunca inferido.

## Problema

"Este pipeline streaming entrega o SLO declarado? Onde está o gargalo —
transporte, checkpoint, estado ou sink?"

## Pré-requisitos

`sparkforge-aws` instalado; um ou mais de: fonte `.py` Structured Streaming,
`StreamingQueryProgress` (JSON), dump Kafka/MSK/Kinesis, dump Flink, contrato
SLO declarado.

## Passo a passo

```bash
# fonte streaming (código) — facts estáticos: source, sink, checkpoint, trigger
sparkforge-aws analyze streaming --path jobs/ --artifact source \
  --out .sparkforge_aws/facts-streaming.json

# transporte — dump observado do mensageiro
sparkforge-aws analyze transport --artifact kafka --path kafka-dump.json \
  --out .sparkforge_aws/facts-transport.json

# julgar tudo junto
sparkforge-aws judge --facts .sparkforge_aws/facts-streaming.json \
  --facts .sparkforge_aws/facts-transport.json \
  --out .sparkforge_aws/findings.json
```

Para avaliar um **SLO declarado contra o observado**, componha facts por
`--mode slo` (quatro observações suportadas: progress de batch, saída de sink,
lag Kafka, iterator age Kinesis):

```bash
sparkforge-aws analyze streaming-composition \
  --facts slo-contract.facts.json --facts progress.facts.json \
  --mode slo --slo-name throughput --query-name orders-query \
  --out slo-evaluation.facts.json
```

## Saída esperada / interpretação

Findings `streaming*`: checkpoint, backpressure, SLO `met`/`violated` pelo
comparador observado, e `streaming.slo.unresolved` quando falta identidade,
unidade canônica, timestamps ou janela declarada coberta. `met`/`violated`
significam **somente o comparador no artefato** — não disponibilidade nem
saúde end-to-end.

## Verificação

Facts carregam `provenance` do artefato lido; `unresolved` conta como ponto
cego explícito, nunca descartado — compare a contagem antes de concluir.

## Limitações

Sem acesso a Spark, Kafka, Kinesis ou AWS em modo offline — tudo vem do
artefato fornecido. Pipeline cross-engine exige selectors exatos (`--mode
pipeline`): zero ou múltiplos matches por node viram
`streaming.pipeline.unresolved`.

## Erros comuns

| Sintoma | Causa | Ação |
|---|---|---|
| `streaming.slo.unresolved` | janela declarada não coberta ou timestamp ausente | forneça o progress/métrica que cobre a janela do contrato |
| `streaming.pipeline.unresolved` | selector casou 0 ou 2+ nodes | refine o `kind`/atributo escalar do pipeline JSON |
| facts vazios | `--artifact` errado para o dump | `source` para código; `progress` para StreamingQueryProgress |

## Uso por agentes

Skill `review-structured-streaming` (separar declaração, medida temporal e
resultado) e `analyze-streaming-composition` (correlacionar facts sem
intuição); coordenador `streaming-realtime-architect` para a investigação
ponta a ponta.
