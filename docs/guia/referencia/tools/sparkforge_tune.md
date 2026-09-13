<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge_tune`

**Efeito:** Só leitura: não grava nada e não acessa a rede.

## O que faz

Configuracao Spark DERIVADA da medida, com a procedencia de cada propriedade. Verbo de topo, nao um `analyze`: nao extrai nada de artefato, consome facts JA extraidos -- mesma razao de `benchmark`, `fuse`, `sparkforge_workload`, `sparkforge_capacity` e `sparkforge_finops`. Deriva UMA propriedade, `spark.sql.shuffle.partitions`, a partir de `spark.stage.shuffle.write_bytes` medido sobre o alvo de tamanho de particao -- o default documentado do AQE, ou `spark.sql.adaptive.advisoryPartitionSizeInBytes` quando o run declara um. A formula e a base viajam dentro da resposta. A VERSAO MUDA O SIGNIFICADO: com AQE default (Spark 3.2+, portanto Glue 4.0 e 5.x) o numero e o PISO de paralelismo inicial que o motor coalesce; sem AQE (Glue 3.0, Spark 3.1.1) e o numero FINAL de particoes. O QUE ESTA TOOL RECUSA: (1) aplicar -- nenhum caminho do codigo escreve configuracao, e cada proposta carrega o nivel de seguranca do 34 (`REVIEW` para paralelismo); (2) derivar sem base medida -- as outras propriedades do 11 saem em `refused` com a medida que as destravaria, nunca omitidas; (3) um valor magico global, que e trocar um numero sem razao por outro com aparencia de calculo; (4) ordenar proposta por ganho estimado, o mesmo contrafactual que `sparkforge_finops` recusa.

## Parâmetros

| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `facts_path` | string | sim | Arquivo de facts (JSON) com `spark.stage.shuffle` do run e, quando houver, `spark.conf_effective`, `pyspark.conf_set` e `tf.spark_conf` -- tipicamente o `--out` de `sparkforge_analyze_event_log`, fundido com os outros. |

## Na CLI

[`sparkforge tune`](../cli/tune.md)

## Capacidade

derive Spark configuration from the measured shuffle

## Anotações MCP

| Anotação | Valor |
|---|---|
| `destructiveHint` | `false` |
| `idempotentHint` | `true` |
| `openWorldHint` | `false` |
| `readOnlyHint` | `true` |
