<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge_lakeformation_matrix`

**Efeito:** Só leitura: não grava nada e não acessa a rede.

## O que faz

Eixo de VERSAO de Lake Formation por runtime Glue: filesystem S3 default, FGAC por caminho (GlueContext contra Spark-native, leitura contra escrita), DDL/DML e Full Table Access -- cada celula com a frase da fonte quando ela existe. Use ANTES de afirmar que um runtime suporta ou nao suporta algo nesta area: a pagina de consideracoes da AWS nao tem eixo de versao, e aplicar a um Glue 5.1 uma limitacao que era do 5.0 e o erro que mais engana aqui. NAO julga configuracao nenhuma e NAO estima ganho: devolve o que as paginas declaram, e o que elas NAO declaram sai como `not_declared`, que e diferente de `not_supported`. Runtime fora da matriz sai `unresolved` com o que destravaria -- nunca palpite por analogia com a versao vizinha.

## Parâmetros

| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `axis` | string | não | Eixo (ex.: `fgac_spark_native_write`). Sem ele, todos. |
| `detail_level` | string: `summary`, `normal`, `full` | não | `summary` omite fonte, frase e nota. |
| `runtime` | string | não | Versao de Glue (ex.: `5.1`). Sem ela, todas as cobertas. |

## Na CLI

[`sparkforge lakeformation matrix`](../cli/lakeformation.md)

## Capacidade

read the Lake Formation version axis for a Glue runtime

## Anotações MCP

| Anotação | Valor |
|---|---|
| `destructiveHint` | `false` |
| `idempotentHint` | `true` |
| `openWorldHint` | `false` |
| `readOnlyHint` | `true` |
