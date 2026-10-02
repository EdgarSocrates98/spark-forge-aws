---
name: analyze-flink-job
description: "Use quando houver dump JSON/JSONL de job Apache Flink ou Managed Flink e for preciso separar checkpoint, backpressure, state, configuração e métricas observadas sem inventar capacidade, limiar ou exatamente-once."
metadata:
  sparkforge_contract: v1
  evals: evals/evals.json
  references:
  - references/README.md
  - references/README.md
  - ../_shared/references/evidence-first.md
  - ../_shared/references/evaluation-contract.md
  - ../_shared/references/operational-safety.md
  - ../../knowledge/flink-streaming.md
  scripts:
  - scripts/validate_evidence.py
  primary_verbs:
  - sparkforge analyze flink
  - sparkforge judge
subagent: true
agent: streaming-realtime-architect
---

# Analyze Flink Job

Analise somente artefatos Flink/Managed Flink já salvos. O analyzer é offline:
não chama Flink, AWS, CloudWatch ou provider. O namespace `flink.*` descreve o
runtime upstream; `managed_flink.*` descreve o serviço gerenciado. Um não prova
capacidade, versão ou comportamento do outro.

## Procedimento

1. Confirme o domínio e o runtime declarado no caso. Se o dump não trouxer a
   versão ou a medição necessária, reporte o `*.unresolved`; não preencha com
   default.
2. Extraia facts:

   ```bash
   sparkforge analyze flink --path <dump.json-ou-diretorio> --artifact flink --out .sparkforge/facts_flink.json
   ```

   Para Amazon Managed Service for Apache Flink, use `--artifact managed_flink`.
   O resultado pode conter `flink.job`, `flink.operator`, `flink.checkpoint`,
   `flink.state`, ou `managed_flink.application`, `managed_flink.config`,
   `managed_flink.connector`, `managed_flink.metric`. Confira os
   `*.unresolved` antes de julgar.
3. Julgue fatos observados:

   ```bash
   sparkforge judge --facts .sparkforge/facts_flink.json --show-skipped
   ```

   Em MCP, a mesma extração é `sparkforge_analyze_flink`.

   `SF-FLINK-001` só reage a status de checkpoint explicitamente `FAILED`.
   `SF-FLINK-002` só reage a medida positiva de backpressure. A ausência da
   métrica não é zero e não gera finding.
4. Correlacione checkpoint e state com logs, restart, source, sink, backlog,
   throughput e janela de medição. Um finding estrutural não fecha causa raiz.
5. Antes de propor mudança de paralelismo, state backend, checkpoint ou
   capacidade, estabeleça baseline e altere uma variável principal. Valide
   contagem, schema, chave declarada e agregados; esses proxies não provam
   identidade completa do resultado.

## Limites

- Não inferir exactly-once a partir de checkpoint presente.
- Não transformar backpressure isolado em incidente sem série comparável.
- Não misturar Apache Flink com Managed Flink.
- Não afirmar ganho, custo ou limiar sem medição e `fact_id`.
- Não executar alteração no job, cluster, application ou AWS.

## Entrega

Separar facts, findings, unresolved, hipótese e recomendação. Toda
recomendação usa `title`, `severity`, `confidence`, `evidence`, `root_cause`,
`proposed_change`, `expected_effect`, `risks`, `tradeoffs`, `validation` e
`rollback`. Declare o runtime observado, fonte de cada evidência e o que ainda
precisa ser coletado.

## Protocolo

Siga `AGENT_PROTOCOL.md`: abra/recupere o case, consulte `sparkforge_next_step`,
use `sparkforge_rules_lookup` para regra e fonte, valide a saída e encaminhe
qualquer mutação ao operador. A skill não executa manutenção destrutiva; sobe
a decisão ao operador. Para correlacionar transporte, use
`sparkforge_analyze_transport` quando houver dump compatível.

## Quando NÃO usar

Não use para código PySpark, event logs sem vocabulário Flink ou para alterar
cluster/serviço. Encaminhe collector live ao operador.

## Referência rápida

`fact_id` ancora observação; `*.unresolved` nomeia lacuna; finding exige
`validation` e recomendação reversível com `rollback`.

## Red flags

Exactly-once, capacidade, custo ou saúde sem medida são hipótese, não fato.

## Contrato de qualidade SparkForge (v1)

Separe facts, findings e unresolved; preserve `fact_id`, fonte, `validation` e
`rollback` em toda recomendação.

## Runtime e escopo

Rode `sparkforge judge --facts <facts.json> --show-skipped` e leia `runtime`,
`detected_from`, `divergences` e `reason: runtime_scope`. Runtime deve vir de
facts reextraídos ou de versão concreta declarada; não invente versão. Regras
fora do `runtime_scope` são recusadas/puladas, não equivalem a ausência de finding.
