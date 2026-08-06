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
4. `sparkforge judge --facts .sparkforge/tf_facts.json --show-skipped` aplica `SF-GLUE-001`, `SF-GLUE-002`, `SF-GLUE-003` e `SF-GLUE-006`. Não precisa de `--glue`: o `tf.attribute` de `key: glue_version` extraído no passo 2 já é a fonte, e a saída devolve o campo `runtime` com o que foi usado — `detected_from: ["terraform"]` confirma a origem. Passe `--glue 5.1` só quando o `.tf` declara a versão por `var.`/`local.` (o extrator não adivinha a referência) e você a conhece de fonte confiável. Com `runtime.glue` vazio, as seis regras Glue são puladas com `reason: runtime_scope` em `--show-skipped`: decisão de capacidade sem o eixo Glue coberto, e você precisa saber disso antes de recomendar worker.
5. **A definição real da API não alimenta a detecção.** O artefato de `collect glue-job` do passo 3 é comparação de drift — não existe extrator que o transforme em fact, então ele nunca preenche `runtime`. Se o drift for justamente na versão, `runtime` continua mostrando o que o Terraform declara, não o que está rodando; nesse caso declare a versão real com `--glue` e trate a diferença como achado.
6. `SF-GLUE-004` (retry sobre escrita não idempotente) exige facts de duas fontes — `tf.attribute` **e** `pyspark.write`. Rode também `sparkforge analyze pyspark --path <job.py> --out .sparkforge/py_facts.json` e passe os dois arquivos na mesma chamada: `--facts` é repetível (`sparkforge judge --facts .sparkforge/tf_facts.json --facts .sparkforge/py_facts.json`), e `judge` une e deduplica as listas antes de julgar. Julgar os dois arquivos separados nunca faz a regra disparar, porque nenhum dos dois sozinho carrega as duas metades da evidência — e unir os facts também é o que mantém a versão do `.tf` disponível para a regra ser avaliada.
7. `SF-GLUE-005` (worker maior sem evidência de spill) **dispara**, e é a regra que existe para segurar a sua mão exatamente aqui — mas ela exige três coisas, e nenhuma responde sozinha:

   ```bash
   sparkforge analyze terraform-diff --before <dir-antes> --after <dir-depois> --out .sparkforge/tf_diff.json
   sparkforge analyze event-log --path <log>.jsonl --out .sparkforge/facts_eventlog.json
   sparkforge judge --facts .sparkforge/tf_diff.json --facts .sparkforge/facts_eventlog.json --show-skipped
   ```

   O `terraform-diff` marca `tf.attribute` de `worker_type` com `changed: true` — é o que diz **o que mudou**, e por isso exige os dois estados do módulo em disco, não um só. O event log traz `spark.job.spill_summary` (zero spill) e `spark.executor.memory_usage` — essa última é o que separa "medimos e não havia limitação de memória" de "ninguém olhou". Sem o diff, ou sem um event log real do run, a regra sai em `skipped` com `reason: requires_facts`, e aí a recomendação de worker maior é sua, não da regra: rotule como hipótese.

## Qual eixo aumentar

Não decida o eixo (workers, worker type, disco, Auto Scaling) sem cruzar a evidência de capacidade com a de execução. A tabela completa de decisão está em `knowledge/glue/workers-and-capacity.md` seção 2 — CPU alta e equilibrada aponta para mais workers, heap alto com spill aponta para worker maior (série R dobra memória com o mesmo vCPU), `DISK_NO_SPACE_ERROR` aponta para mais disco, mas executor perdido sem OOM de heap aponta para `memoryOverhead` (não worker), skew aponta para corrigir a chave (não capacidade), e `workerUtilization` baixo aponta para Auto Scaling ou reduzir workers, nunca para aumentar.

## Referência rápida

| Regra | Fact que consome | O que acusa |
|---|---|---|
| `SF-GLUE-001` | `tf.attribute` | Auto Scaling habilitado junto com `number_of_workers` fixo — contraditório, e deixa a capacidade efetiva ambígua |
| `SF-GLUE-002` | `tf.resource` + ausência de `tf.observability.spark_ui` no mesmo recurso | Observabilidade ausente — sem ela, nenhuma decisão de capacidade futura tem baseline. Um achado por job sem observabilidade |
| `SF-GLUE-003` | `tf.attribute` | `max_concurrent_runs` acima de 1 com bookmark habilitado — risco de reprocessamento ou corrida |
| `SF-GLUE-004` | `tf.attribute` + `pyspark.write` (facts combinados) | Retry configurado sobre escrita append sem controle de idempotência |
| `SF-GLUE-005` | `tf.attribute` com `changed: true` (via `analyze terraform-diff`) + `spark.job.spill_summary` + `spark.executor.memory_usage` | Worker maior sem evidência de limitação de memória — exige os dois estados do Terraform e um event log real |
| `SF-GLUE-006` | `tf.attribute` | Segredo em default argument — achado de segurança, tem precedência sobre qualquer recomendação de performance |

Limiares e severidade vêm de `sparkforge rules lookup --id <ID>`, nunca de memória.

## Quando NÃO usar

- Ainda não sabe o gargalo: comece por `analyze-spark-ui`, `diagnose-oom` ou `diagnose-data-skew`.
- O problema é código, layout Parquet/Iceberg ou skew: resolva a causa antes de mexer em workers — capacidade não corrige nenhum dos três.
- A revisão é só da configuração declarada em IaC, sem decisão de capacidade a fazer: use `review-glue-terraform`.
- O volume do job varia muito execução a execução: veja primeiro `optimize-variable-volume-job` — um único perfil de capacidade pode estar errado pros dois extremos ao mesmo tempo.

## Red flags

- Escalar workers para esconder skew, small files ou `collect` no driver.
- Recomendar worker maior sem `SF-UI-003` (spill) ter disparado. `SF-GLUE-005` pega isso — mas só se você tiver dado a ela o diff do Terraform **e** o event log; se ela saiu em `skipped` por `requires_facts`, nada te impediu automaticamente e a recomendação corre sem rede.
- Comparar só runtime de parede e ignorar DPU-hours — duração sozinha esconde superprovisão.
- Copiar configuração de uma versão de Spark/Glue para outra sem confirmar com `sparkforge runtime detect`.

## Preservar o resultado, com o verbo que produz a evidência

Aumentar worker ou mudar o tipo não move o dado, e dizer isso é metade da regra. A outra
metade é o que **move**: `spark.sql.shuffle.partitions` muda quantos arquivos a escrita produz
e qual linha cai em qual arquivo, e todo consumidor que dependa disso vê outra coisa com a
contagem idêntica. Declare em qual das duas metades a sua recomendação está.

`sparkforge funcval plan --facts <facts.json> --out <plano.json>` deriva o plano — `--facts`
é repetível, porque o alvo vem do `pyspark.write` e o schema e os agregados vêm do
`catalog.table_schema` —, e `sparkforge funcval compare --plan <plano.json> --before
<antes.json> --after <depois.json>` compara os dois lados **que o operador mediu**: nenhum dos
dois executa consulta, roda Spark ou chama AWS. Tools MCP: `sparkforge_funcval_plan` e
`sparkforge_funcval_compare`. O plano é a evidência do gate `functional_validation_defined`, e
`ROUTE-015` é a rota que manda defini-lo. O lado `--before` só existe se alguém o mediu
**antes** de a mudança tocar o alvo — um `overwrite` no meio o apaga sem deixar rastro.

Os quatro eixos são **proxies**, e escrever o contrário promete o que a ferramenta não
entrega: contagem, schema, chaves e agregados iguais **não provam** que o dado é o mesmo — duas
linhas podem trocar valores entre si e os quatro passam. Escreva "nenhum dos quatro proxies
detectou divergência", nunca "o resultado é idêntico". Sem `--key`, a chave de negócio sai em
`undeclared_axes` com a razão, e isso vai dito. `SF-FVAL-005` acesa invalida a leitura das
outras quatro.

## Protocolo

Siga `AGENT_PROTOCOL.md`. Resumo: abra o case antes de analisar; chame `next_step` antes de
escolher skill; nenhum número sem `fact_id`; `rules_lookup` em vez de memória para limiar e
versão; `validate_output` antes de apresentar; reporte `unresolved`; confirme o runtime;
manutenção destrutiva só com confirmação explícita. E **derive o plano de validação funcional** com `funcval plan` antes de fechar a
recomendação, comparando os dois lados medidos com `funcval compare` — a regra 10, e ela
nomeia o produtor de propósito: exigência sem verbo é prosa.
