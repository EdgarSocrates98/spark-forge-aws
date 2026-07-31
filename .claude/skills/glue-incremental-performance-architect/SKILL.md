---
name: glue-incremental-performance-architect
description: Use quando investigar de ponta a ponta uma biblioteca PySpark no AWS Glue com fluxos full e incremental, latest-per-key sobre tabela Iceberg bilionária, batching por lote, OOM que só aparece depois de horas, ou carga que varia de dezenas a milhões de registros — e for preciso orquestrar as skills especializadas em vez de mexer isoladamente num sintoma. Use também quando a pergunta for "o job incremental tá tão lento quanto o full", "o job só morre de memória depois de um bom tempo rodando" ou "esse job tem dois jeitos de rodar e não sei qual tá causando o problema", mesmo que ninguém fale em full/incremental. Se você está prestes a mexer em workers, shuffle partitions ou cache antes de mapear a biblioteca inteira, pare — é exatamente isso que este documento existe para evitar. Leia `PROMPT_INICIAL_MESTRE.md` primeiro.
---

# Glue Incremental Performance Architect

Tuning localizado num job com dois fluxos é a forma mais cara de errar aqui: corrige um sintoma no incremental enquanto a causa real está no full, ou vice-versa, e o próximo ciclo reproduz o problema porque nada na arquitetura mudou. Esta skill não substitui as skills especializadas — ela decide a ordem em que rodam e recusa fechar a investigação enquanto full, incremental, latest-per-key, batching e OOM não estiverem todos mapeados.

## Sequência obrigatória

### 1. Leia `PROMPT_INICIAL_MESTRE.md`

A missão completa, os 20 entregáveis esperados, e por que "aumentar workers" nunca é a primeira resposta.

### 2. Mapeie a biblioteca

```bash
sparkforge analyze pyspark --path <lib> --out .sparkforge/facts.json
sparkforge analyze call-graph --facts .sparkforge/facts.json --out .sparkforge/callgraph.json
```

`callgraph.reachable_spark_work` mostra, por função, todo o trabalho Spark (`pyspark.*`) alcançável a partir de cada entrypoint — é como se separa o que o fluxo full aciona do que o incremental aciona sem ler a biblioteca inteira à mão. Duas entradas com call graphs que convergem no mesmo trabalho pesado é o primeiro sinal de scan global disfarçado de incremental.

### 3. Julgue o inventário

```bash
sparkforge judge --facts .sparkforge/facts.json --glue <versão> --show-skipped
```

Preste atenção especial a `SF-PY-004` (action ou write dentro de loop): se aparecer, domina qualquer outro diagnóstico e mascara o resto — `ROUTE-004` em `routing.yaml` manda direto para `analyze-batch-loop` quando isso acontece, antes de qualquer outra investigação.

### 4. Deixe next-step orquestrar as skills especializadas

```bash
sparkforge next-step --repo <repo> --findings .sparkforge/findings.json
```

Chame de novo depois de cada rodada de achados novos — a árvore de roteamento manda para `design-incremental-processing`, `optimize-latest-per-key`, `analyze-batch-loop`, `diagnose-oom`, `optimize-parquet-layout`, `optimize-iceberg-table` e `review-glue-terraform` na ordem que a evidência pede, não na ordem que parece intuitiva.

### 5. Formule a arquitetura-alvo

Só depois que full, incremental, latest-per-key, batching e OOM estiverem todos mapeados e classificados — nunca antes, mesmo que um deles já pareça óbvio.

### 6. Crie experimentos, meça e valide

```bash
sparkforge validate --findings .sparkforge/findings.json
```

Uma variável principal por experimento; sem baseline capturado (`benchmark-pyspark-job`) não há como provar impacto.

## Referência rápida

Não decida à mão qual skill vem a seguir — estas são as correlações que `routing.yaml` já codifica; rode `next-step` e leia `reason` e `evidence` na saída em vez de memorizar a tabela.

| Etapa da investigação | Regra de roteamento | Skill de apoio |
|---|---|---|
| mapear trabalho oculto, sem fact extraído ainda | `ROUTE-002` | `analyze-library-call-graph` |
| dois entrypoints, fluxos ainda não separados | `ROUTE-003` | `design-incremental-processing` |
| `SF-PY-004` presente — action/write em loop | `ROUTE-004` | `analyze-batch-loop` |
| `SF-UI-005` presente — executor perdido sem OOM de heap | `ROUTE-005` | `diagnose-oom` |
| `SF-PQ-001` ou `SF-ICE-001` presente — small files dominando | `ROUTE-009` | `optimize-parquet-layout` |
| `SF-ICE-002` ou `SF-ICE-003` presente — dívida de metadados | `ROUTE-010` | `optimize-iceberg-table` |
| facts extraídos, zero findings de código | `ROUTE-014` | `review-glue-terraform` |
| gargalo dominante identificado, sem baseline | `ROUTE-012` | `benchmark-pyspark-job` |

`optimize-latest-per-key` não tem regra de roteamento própria hoje: acione manualmente para cada tabela incremental relevante depois de `design-incremental-processing` separar os fluxos — é o passo do documento mestre que a árvore automática ainda não cobre.

## Por que "fechar cedo" é o erro mais caro aqui

Encerrar só com mais workers, mudança de `shuffle.partitions`, hint de broadcast, compactação ou cache — sem explicar a relação entre full, incremental, estado atual, scans globais e commits Iceberg — reproduz exatamente o sintoma que `PROMPT_INICIAL_MESTRE.md` existe para evitar. Nenhuma das 16 regras de `routing.yaml` aponta para "aumentar capacidade" como skill recomendada: se a investigação está prestes a terminar assim, é sinal de que full, incremental, latest-per-key, batching ou OOM ainda não foram mapeados por completo, não de que a resposta é capacidade.

## Quando NÃO usar

- O job tem um único fluxo simples e um sintoma isolado: use `sparkforge-diagnose` ou a skill específica direto.
- Você só quer revisar código, PR ou Terraform, sem investigar full/incremental: use a skill focada correspondente.
- Já mapeou tudo e falta apenas medir: vá direto para `benchmark-pyspark-job`.

## Red flags

- Fazer tuning localizado antes de mapear biblioteca, actions, batching, latest-per-key e OOM.
- Encerrar só com "mais workers", `shuffle.partitions`, broadcast, compactação ou cache, sem separar os DAGs de full e incremental.
- Tratar `optimize-latest-per-key` como opcional quando existe cálculo de mais recente por chave sobre histórico Iceberg — não há regra de roteamento que lembre disso por você.
- Ignorar `SF-PY-004` quando presente e seguir investigando joins ou skew antes de resolver o loop.

## Protocolo

Siga `AGENT_PROTOCOL.md`. Resumo: abra o case antes de analisar; chame `next_step` antes de
escolher skill; nenhum número sem `fact_id`; `rules_lookup` em vez de memória para limiar e
versão; `validate_output` antes de apresentar; reporte `unresolved`; confirme o runtime;
manutenção destrutiva só com confirmação explícita.
