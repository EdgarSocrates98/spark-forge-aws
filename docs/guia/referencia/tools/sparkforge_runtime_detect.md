<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge_runtime_detect`

**Efeito:** Só leitura: não grava nada e não acessa a rede.

## O que faz

Deriva glue/emr/spark/python/iceberg/athena dos facts ja extraidos e dos parametros informados, usando as matrizes oficiais de compatibilidade do Glue e do EMR. Com `facts_path`, a versao OBSERVADA pelos extratores (`tf.attribute` glue_version, `spark.runtime_version`, `emr.cluster`) alimenta a deteccao -- ninguem precisa saber a versao de cor. Divergencia entre fontes nao e resolvida escolhendo uma: e reportada em `divergences`, porque aplicar limiar ou API da versao errada invalida qualquer recomendacao seguinte.

## Parâmetros

| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `athena` | string | não |  |
| `emr` | string | não | Release do EMR on EC2, nas duas grafias ('emr-7.5.0' ou '7.5.0'). DECLARACAO, nao observacao: perde para o event log e para um dump de describe-cluster, e discordar de um deles vira divergencia reportada em `runtime.divergences`, nunca valor substituido em silencio. |
| `facts_path` | string ou array de string | não | Um caminho, ou varios: os facts sao unidos e deduplicados antes de derivar as fontes de versao. |
| `glue` | string | não |  |
| `iceberg` | string | não |  |
| `python` | string | não |  |
| `spark` | string | não |  |

## Na CLI

[`sparkforge runtime detect`](../cli/runtime.md)

## Capacidade

detect runtime and version divergence

## Anotações MCP

| Anotação | Valor |
|---|---|
| `destructiveHint` | `false` |
| `idempotentHint` | `true` |
| `openWorldHint` | `false` |
| `readOnlyHint` | `true` |
