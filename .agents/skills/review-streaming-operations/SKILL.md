---
name: review-streaming-operations
description: "Use quando houver um contrato declarativo de streaming e for necessário revisar SLO, FinOps, segurança, serving e lakehouse sem inventar medição, preço ou eficácia operacional."
metadata:
  sparkforge_contract: v1
  evals: evals/evals.json
  references:
  - references/README.md
  - ../_shared/references/evidence-first.md
  - ../_shared/references/evaluation-contract.md
  - ../_shared/references/operational-safety.md
  - ../../knowledge/streaming-operations.md
  - ../../knowledge/streaming-format-serving-matrix.md
  scripts:
  - scripts/validate_evidence.py
  primary_verbs:
  - sparkforge-aws analyze streaming-ops
  - sparkforge-aws judge
subagent: true
agent: streaming-realtime-architect
---

# Review Streaming Operations

Use um contrato JSON salvo localmente. A análise mede declarações e preserva
lacunas; não consulta AWS e não calcula preço.

```bash
sparkforge-aws analyze streaming-ops \
  --path streaming-operations.json \
  --out streaming-operations-facts.json
sparkforge-aws judge --facts streaming-operations-facts.json
```

## Procedimento

1. Confirme que SLO tem métrica, unidade, janela, origem e `target` numérico.
2. Confirme que FinOps traz medida observada, unidade, período, região, tier e
   origem. Nunca transforme DPU-seconds, vCPU-hours ou bytes em preço sem uma
   base de custo declarada.
3. Revise controles de transporte, autenticação, TLS, KMS, VPC, Secrets
   Manager, cross-account e resource policy. Valores que parecem segredo são
   redigidos e viram `unresolved`.
4. Compare serving e formato lakehouse com a matriz de conhecimento; não
   derive compatibilidade, latência ou exactly-once por nome do produto.
5. Leia cada `streaming_ops.unresolved` antes de julgar. Proponha o artefato ou
   experimento que destrava cada lacuna.

### Kafka/MSK transport evidence

Para dump sanitizado de Kafka ou MSK, rode o analyzer de transporte antes da
composição:

```bash
sparkforge-aws analyze transport --artifact kafka --path kafka-dump.json \
  --out kafka-facts.json
sparkforge-aws judge --facts kafka-facts.json --show-skipped
```

Leia `kafka.partition` para ISR observado e `kafka.lag.series` para uma série
explícita por `group/topic/partition`. `SF-STREAMOBS-003` só dispara quando o
`replication_factor` observado supera `isr_count`; `SF-STREAMOBS-004` exige pelo
menos duas observações timestampadas e lag crescente em todos os passos. Lag
legado em `consumer_groups[].offsets` é snapshot, não tendência. Ausência ou
timestamp inválido permanece `kafka.unresolved`; não invente causa, throughput,
SLO ou saúde do consumidor.

### Declared cross-engine pipeline

Quando o caso precisa correlacionar CDC, transporte, processador e sink, use
um contrato JSON versionado e selectors exatos:

```bash
sparkforge-aws analyze streaming-composition \
  --facts cdc-facts.json --facts kafka-facts.json --facts flink-facts.json \
  --facts iceberg-facts.json --mode pipeline \
  --pipeline-path pipeline.json --out pipeline-facts.json
```

Cada node precisa de exatamente um match por `kind` e atributos escalares;
zero ou múltiplos matches viram `streaming.pipeline.unresolved`. Edges só são
verified com os dois endpoints verified. Leia `source_fact_ids` e provenance;
não transforme o resultado em prova de topologia descoberta, latência,
throughput, exactly-once, saúde ou causalidade.

## Limites

- declaração de controle não prova eficácia em runtime;
- o extrator não coleta IAM, KMS, VPC, CUR ou métricas de serviços;
- serving e formato são evidência de desenho, não benchmark;
- recomendações devem conter evidência, risco, trade-off, validação e rollback.

## Quando NÃO usar

Não use para calcular preço, coletar AWS ou declarar eficácia de controle sem
artefato de execução correspondente.

## Referência rápida

`fact_id` ancora a declaração; `*.unresolved` preserva ausência; `validation` e
`rollback` fecham a recomendação sem expor segredo.

## Red flags

SLO sem janela, FinOps sem unidade/período, segurança sem evidência de runtime e
serving sem benchmark são lacunas, não sucesso.

## Contrato de qualidade SparkForge (v1)

Separe medida declarada, finding e hipótese; não copie secrets e sempre nomeie
validation, risco e rollback.

## Protocolo

Siga `AGENT_PROTOCOL.md`, não executa manutenção destrutiva; sobe qualquer
mutação live ao operador.

## Runtime e escopo

Rode `sparkforge-aws judge --facts <facts.json> --show-skipped` e leia `runtime`,
`detected_from`, `divergences` e `reason: runtime_scope`. Runtime deve vir de
facts reextraídos ou de versão concreta declarada; não invente versão. Regras
fora do `runtime_scope` são recusadas/puladas, não equivalem a ausência de finding.
