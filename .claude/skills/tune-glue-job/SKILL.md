---
name: tune-glue-job
description: Use quando for ajustar workers, worker type, Auto Scaling, execution class ou argumentos de um job Glue depois de já ter um gargalo comprovado — não para descobri-lo. Use também quando a pergunta for "aumenta os workers?", "põe mais DPU", "troca pra worker maior" ou "liga Auto Scaling", mesmo sem esse vocabulário. Se você está prestes a recomendar mais workers a partir só do código ou de instinto, rode `sparkforge analyze terraform`, `sparkforge collect glue-job` e `sparkforge judge` em vez disso — o catálogo SF-GLUE-* aponta contradição de Auto Scaling, observabilidade ausente e retry sobre escrita não idempotente antes de qualquer decisão de capacidade, e a tabela de decisão em knowledge/glue/workers-and-capacity.md tem capacidade como resposta errada em metade dos casos.
---

# Tune AWS Glue Job

Ajustar capacidade sem um gargalo comprovado é tuning por intuição, e a tabela de decisão em `knowledge/glue/workers-and-capacity.md` seção 2 mostra por que o instinto erra tanto: das oito evidências mais comuns, quatro têm "mais capacidade" como a resposta errada. Esta skill não descobre o gargalo — ela ajusta a configuração depois que ele já está comprovado em outro lugar.

## Procedimento

1. **Confirme que já existe baseline.** CPU, heap, spill, GC e distribuição de task vêm de `analyze-spark-ui`; classificação de OOM vem de `diagnose-oom`; skew vem de `diagnose-data-skew`. Sem isso, pare e volte para lá — não há eixo certo sem essa evidência.
2. `sparkforge analyze terraform --path <dir> --out .sparkforge/tf_facts.json` extrai `tf.attribute`, `tf.resource` e `tf.observability.spark_ui` da definição declarada em Terraform.
3. `sparkforge collect glue-job --repo . --job-name <nome> --now <ISO8601>` baixa a definição real via API do Glue, para comparar contra o declarado e achar drift entre IaC e o que está rodando.
4. `sparkforge judge --facts .sparkforge/tf_facts.json --glue <versão> --show-skipped` aplica `SF-GLUE-001`, `SF-GLUE-002`, `SF-GLUE-003` e `SF-GLUE-006`.
5. `SF-GLUE-004` (retry sobre escrita não idempotente) exige facts de duas fontes — `tf.attribute` **e** `pyspark.write`. `judge` só aceita um arquivo de facts por chamada: rode também `sparkforge analyze pyspark --path <job.py> --out .sparkforge/py_facts.json`, combine as duas listas JSON num único arquivo, e julgue esse combinado se quiser essa regra avaliada.
6. `SF-GLUE-005` (worker maior sem evidência de spill) está `blocked_on: extrator-de-diff-terraform` no catálogo — inerte por desenho até existir um extrator de diff. Ela não vai disparar hoje. Se você está recomendando worker maior sem `SF-UI-003` (spill) ter disparado em `analyze-spark-ui`, essa recomendação é sua, não da regra — rotule como hipótese, não como achado.

## Qual eixo aumentar

Não decida o eixo (workers, worker type, disco, Auto Scaling) sem cruzar a evidência de capacidade com a de execução. A tabela completa de decisão está em `knowledge/glue/workers-and-capacity.md` seção 2 — CPU alta e equilibrada aponta para mais workers, heap alto com spill aponta para worker maior (série R dobra memória com o mesmo vCPU), `DISK_NO_SPACE_ERROR` aponta para mais disco, mas executor perdido sem OOM de heap aponta para `memoryOverhead` (não worker), skew aponta para corrigir a chave (não capacidade), e `workerUtilization` baixo aponta para Auto Scaling ou reduzir workers, nunca para aumentar.

## Referência rápida

| Regra | Fact que consome | O que acusa |
|---|---|---|
| `SF-GLUE-001` | `tf.attribute` | Auto Scaling habilitado junto com `number_of_workers` fixo — contraditório, e deixa a capacidade efetiva ambígua |
| `SF-GLUE-002` | `tf.attribute` / ausência de `tf.observability.spark_ui` | Observabilidade ausente — sem ela, nenhuma decisão de capacidade futura tem baseline |
| `SF-GLUE-003` | `tf.attribute` | `max_concurrent_runs` acima de 1 com bookmark habilitado — risco de reprocessamento ou corrida |
| `SF-GLUE-004` | `tf.attribute` + `pyspark.write` (facts combinados) | Retry configurado sobre escrita append sem controle de idempotência |
| `SF-GLUE-005` | inerte — falta extrator de diff | Worker maior recomendado sem baseline de spill comprovado; hoje isso é julgamento seu, não da regra |
| `SF-GLUE-006` | `tf.attribute` | Segredo em default argument — achado de segurança, tem precedência sobre qualquer recomendação de performance |

Limiares e severidade vêm de `sparkforge rules lookup --id <ID>`, nunca de memória.

## Quando NÃO usar

- Ainda não sabe o gargalo: comece por `analyze-spark-ui`, `diagnose-oom` ou `diagnose-data-skew`.
- O problema é código, layout Parquet/Iceberg ou skew: resolva a causa antes de mexer em workers — capacidade não corrige nenhum dos três.
- A revisão é só da configuração declarada em IaC, sem decisão de capacidade a fazer: use `review-glue-terraform`.
- O volume do job varia muito execução a execução: veja primeiro `optimize-variable-volume-job` — um único perfil de capacidade pode estar errado pros dois extremos ao mesmo tempo.

## Red flags

- Escalar workers para esconder skew, small files ou `collect` no driver.
- Recomendar worker maior sem `SF-UI-003` (spill) ter disparado — lembre que `SF-GLUE-005` está inerte, então nada aqui vai te impedir automaticamente.
- Comparar só runtime de parede e ignorar DPU-hours — duração sozinha esconde superprovisão.
- Copiar configuração de uma versão de Spark/Glue para outra sem confirmar com `sparkforge runtime detect`.

## Protocolo

Siga `AGENT_PROTOCOL.md`. Resumo: abra o case antes de analisar; chame `next_step` antes de
escolher skill; nenhum número sem `fact_id`; `rules_lookup` em vez de memória para limiar e
versão; `validate_output` antes de apresentar; reporte `unresolved`; confirme o runtime;
manutenção destrutiva só com confirmação explícita.
