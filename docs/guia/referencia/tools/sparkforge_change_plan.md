<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge_change_plan`

**Efeito:** Só leitura: não grava nada e não acessa a rede.

## O que faz

Autonomia L1 (§15, produce change): o diff unificado e o diff de rollback de um VALOR de configuracao Spark, achado pela procedencia dos facts -- `tf.spark_conf` (so o par `chave=valor` dentro do `--conf` do Terraform) ou `pyspark.conf_set` (o literal na chamada). O valor vem de `from_tune` (o que `sparkforge_tune` deriva da medida, com a formula em `basis`) ou de `sets` (`chave=valor`). Antes de trocar, confere que o valor do fact ainda esta na linha. Toda chave sem base sai em `refused` com o que a destrava: sem_procedencia_em_arquivo, linha_nao_confere, procedencia_ambigua, valor_nao_literal, valor_redigido, valor_invalido, valor_ja_igual, caminho_fora_da_raiz. O QUE ELA NAO FAZ: nao aplica nem grava nada (`applied: false`), nao gera mudanca de codigo (so valor literal) e nao estima ganho. Para ver o que o diff move nos achados, `sparkforge_change_sandbox`.

## Parâmetros

| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `facts_path` | string ou array de string | sim | Facts do case (a uniao que o judge recebeu). |
| `repo` | string | sim | Raiz usada na extracao dos facts. |
| `from_tune` | boolean | não | Usa o valor que o tune deriva da medida. |
| `sets` | array de string | não | chave=valor, por exemplo spark.sql.shuffle.partitions=320. |

## Na CLI

[`sparkforge change plan`](../cli/change.md), [`sparkforge change sandbox`](../cli/change.md)

## Capacidade

produce a configuration change and try any diff in a sandbox copy

## Anotações MCP

| Anotação | Valor |
|---|---|
| `destructiveHint` | `false` |
| `idempotentHint` | `true` |
| `openWorldHint` | `false` |
| `readOnlyHint` | `true` |
