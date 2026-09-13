<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge lakeformation`

Eixo de VERSAO de Lake Formation por runtime Glue -- capacidade, nao versao de componente.

## Subcomandos

| Subcomando | O que faz |
|---|---|
| [`sparkforge lakeformation access-graph`](#sparkforge-lakeformation-access-graph) | O caminho de acesso como GRAFO, a partir de facts. `is_accessible` e TERNARIO -- `null` e 'o que olhei nao impede', nao 'funciona'. |
| [`sparkforge lakeformation matrix`](#sparkforge-lakeformation-matrix) | Imprime o eixo: filesystem S3 default, FGAC por caminho, DDL/DML e FTA, com a frase da fonte quando ela existe. |

## `sparkforge lakeformation access-graph`

O caminho de acesso como GRAFO, a partir de facts. `is_accessible` e TERNARIO -- `null` e 'o que olhei nao impede', nao 'funciona'.

```bash
sparkforge lakeformation access-graph --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--facts` | sim | texto | sim |  |  |
| `--principal-arn` | não | texto |  | `` |  |
| `--target-table` | não | texto |  | `` |  |

### Tool MCP equivalente

[`sparkforge_lakeformation_access_graph`](../tools/sparkforge_lakeformation_access_graph.md)

## `sparkforge lakeformation matrix`

Imprime o eixo: filesystem S3 default, FGAC por caminho, DDL/DML e FTA, com a frase da fonte quando ela existe.

```bash
sparkforge lakeformation matrix --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--runtime` | não | texto |  |  | Versao de Glue. Sem ela, todas as que a matriz cobre. Versao fora da matriz sai `unresolved` com o que destravaria -- nunca palpite por analogia com a versao vizinha. |
| `--axis` | não | texto |  |  | Eixo especifico (ex.: `fgac_spark_native_write`). Sem ele, todos. |
| `--detail-level` | não | `summary`, `normal`, `full` |  | `full` | `summary` omite fonte, frase e nota. Ver a regra 28 do CLAUDE.md. |

### Tool MCP equivalente

[`sparkforge_lakeformation_matrix`](../tools/sparkforge_lakeformation_matrix.md)
