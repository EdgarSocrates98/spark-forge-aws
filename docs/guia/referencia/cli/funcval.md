<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge funcval`

Validacao funcional: deriva o que medir nos dois lados de uma mudanca e compara antes contra depois. Nao executa nada.

## Subcomandos

| Subcomando | O que faz |
|---|---|
| [`sparkforge funcval compare`](#sparkforge-funcval-compare) | Compara os dois resultados que VOCE mediu contra o plano. Antes contra depois, nunca observado contra catalogo. |
| [`sparkforge funcval plan`](#sparkforge-funcval-plan) | Deriva o plano de validacao (contagem, schema, agregados) dos facts ja extraidos, e grava o artefato que `funcval compare` rele. |

## `sparkforge funcval compare`

Compara os dois resultados que VOCE mediu contra o plano. Antes contra depois, nunca observado contra catalogo.

```bash
sparkforge funcval compare --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--plan` | sim | texto |  |  | Arquivo gerado por `funcval plan --out`. |
| `--before` | sim | texto |  |  | Resultado medido ANTES da mudanca: JSON com `target` e `checks`, um objeto por check. `value: null` exige `unavailable_reason`; check que voce nao mediu fica AUSENTE, nunca zero. |
| `--after` | sim | texto |  |  | Resultado medido DEPOIS, no mesmo contrato. |
| `--out` | não | texto |  |  | Escreve a comparacao (JSON de facts) neste arquivo, que e o que `judge --facts` le. Opcional, ao contrario do `--out` do `plan`: o plano e a entrada do proximo verbo, esta e uma saida terminal. Grava a lista COMPLETA, nunca a pagina -- `--limit` corta o stdout e nao o arquivo. |
| `--kind` | não | texto | sim |  | Filtra por kind. Repetivel. |
| `--limit` | não | texto |  | `50` |  |
| `--cursor` | não | texto |  |  |  |
| `--detail-level` | não | `summary`, `normal`, `full` |  | `full` | Verbosidade da saida. `full` (default) devolve o fato inteiro, com a procedencia dentro de cada item -- e o modo de reauditoria. `normal` declara procedencia e schema_version UMA VEZ no envelope e referencia a procedencia por `provenance_ref`. `summary` reduz cada item a id, kind, medidas, arquivo:linha e simbolo. NAO existe subcomando que busque um fato por id: para ter o fato inteiro de volta, reexecute em `full` e pague o payload inteiro outra vez. |

### Tool MCP equivalente

[`sparkforge_funcval_compare`](../tools/sparkforge_funcval_compare.md)

## `sparkforge funcval plan`

Deriva o plano de validacao (contagem, schema, agregados) dos facts ja extraidos, e grava o artefato que `funcval compare` rele.

```bash
sparkforge funcval plan --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--facts` | sim | texto | sim |  | Arquivo de facts (JSON) gerado por `analyze pyspark --out` ou `analyze catalog-schema --out`. Repetivel, e precisa ser: o alvo vem do `pyspark.write` e o schema/os agregados vem do `catalog.table_schema`, que nenhum verbo produz no mesmo arquivo. |
| `--key` | não | texto | sim |  | Chave de negocio DECLARADA, repetivel. Virgula faz chave COMPOSTA (`--key loja_id,pedido_id` e uma chave de duas colunas, nao duas chaves). Nenhum fact do repositorio nomeia chave de negocio, entao o eixo so existe se voce o declarar -- e o check sai com `origin: declared`. Sem `--key`, o plano escreve o eixo como ausente em `undeclared_axes`. |
| `--out` | sim | texto |  |  | Escreve o plano (JSON de facts) neste arquivo. OBRIGATORIO, ao contrario do `--out` dos verbos de `analyze`: o plano e a entrada de `funcval compare --plan` e a evidencia do gate, nao uma conveniencia. |
| `--kind` | não | texto | sim |  | Filtra por kind. Repetivel. |
| `--limit` | não | texto |  | `50` |  |
| `--cursor` | não | texto |  |  |  |
| `--detail-level` | não | `summary`, `normal`, `full` |  | `full` | Verbosidade da saida. `full` (default) devolve o fato inteiro, com a procedencia dentro de cada item -- e o modo de reauditoria. `normal` declara procedencia e schema_version UMA VEZ no envelope e referencia a procedencia por `provenance_ref`. `summary` reduz cada item a id, kind, medidas, arquivo:linha e simbolo. NAO existe subcomando que busque um fato por id: para ter o fato inteiro de volta, reexecute em `full` e pague o payload inteiro outra vez. |

### Tool MCP equivalente

[`sparkforge_funcval_plan`](../tools/sparkforge_funcval_plan.md)
