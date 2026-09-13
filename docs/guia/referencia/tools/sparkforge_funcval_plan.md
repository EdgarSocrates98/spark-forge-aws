<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge_funcval_plan`

**Efeito:** Grava em disco local (repetir a chamada dá o mesmo resultado).

## O que faz

Deriva O QUE MEDIR nos dois lados de uma mudanca, a partir de facts JA extraidos (`sparkforge_analyze_pyspark` e `sparkforge_analyze_catalog_schema` gravados em disco), e GRAVA o plano em `out_path` -- o artefato que `sparkforge_funcval_compare` rele. Emite `funcval.plan` (um por alvo distinto) e `funcval.unresolved`. Verbo de topo, nao um `analyze`: nao extrai nada de artefato. O QUE ELE RECUSA AFIRMAR, e isso importa mais que o que ele afirma: (1) Os quatro eixos sao PROXIES. Contagem, schema, chaves e agregados iguais NAO provam que o dado e o mesmo -- duas linhas podem trocar valores entre si e os quatro passam; a fase afirma 'nenhum dos quatro proxies detectou divergencia', nunca 'o resultado e identico'. (2) Ele NAO MEDE NADA: nao executa consulta, nao le a tabela, nao chama AWS. Os valores vem do resultado que VOCE produz em cada lado. (3) CHAVE DE NEGOCIO NAO E DERIVAVEL: nenhum kind que os extratores emitem a nomeia (`pyspark.join` da o NUMERO de colunas do `on`, `pyspark.dedup` e `pyspark.window` dao booleanos, particao como proxy foi medida e rejeitada). Ela so entra por `keys`, com `origin: declared` e `derived_from: []` -- e chave declarada errada produz P0 em dado correto, com a diferenca de que fica gravado quem afirmou. Sem `keys`, o eixo sai ESCRITO como ausente em `undeclared_axes`, nunca calado. (4) O catalogo diz QUAIS colunas e tipos existem, e nada mais: o check de `schema` NAO carrega o mapa coluna->tipo, porque a comparacao e sempre antes contra depois -- observado contra declarado e asserção absoluta sobre o dado, que e pergunta de SF-DQ. (5) Alvo que nao casa por string identica com um simbolo do catalogo vira `funcval.unresolved`, nunca alvo adivinhado por sufixo.

## Parâmetros

| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `facts_paths` | array de string | sim | Arquivos de facts (JSON) de `sparkforge_analyze_pyspark` e `sparkforge_analyze_catalog_schema`. Repetivel, e precisa ser: o alvo vem do `pyspark.write` e o schema/os agregados vem do `catalog.table_schema`, que nenhum verbo produz no mesmo arquivo. |
| `out_path` | string | sim | Onde gravar o plano. Obrigatorio: o plano e a entrada de `sparkforge_funcval_compare` e a evidencia do gate, nao uma conveniencia de saida. |
| `cursor` | string | não |  |
| `detail_level` | string: `summary`, `normal`, `full` | não | Verbosidade da saida. `full` (default) devolve o fato inteiro, com a procedencia dentro de cada item -- e o modo de reauditoria. `normal` declara procedencia e `schema_version` UMA VEZ no envelope e referencia a procedencia por `provenance_ref`. `summary` reduz cada item a `id`, `kind`, `measures`, `at` (arquivo:linha) e `symbol`. Nada e apagado em silencio: o que sai do item aparece no envelope. NAO existe verbo que busque um fato por id -- para ter o fato inteiro de volta, reexecute o mesmo verbo em `full` e pague o payload inteiro outra vez. O `id` e estavel entre execucoes, entao serve para casar a linha do resumo com o mesmo fato numa execucao `full`. |
| `keys` | array de string | não | Chaves de negocio DECLARADAS por voce. Cada elemento e uma chave; virgula dentro dele faz chave COMPOSTA (`"loja_id,pedido_id"` e uma chave de duas colunas). Omitir nao e erro: o eixo sai escrito como ausente. |
| `kind` | array de string | não |  |
| `limit` | integer | não |  |

## Na CLI

[`sparkforge funcval plan`](../cli/funcval.md)

## Capacidade

derive what to measure on both sides of a change

## Anotações MCP

| Anotação | Valor |
|---|---|
| `destructiveHint` | `false` |
| `idempotentHint` | `true` |
| `openWorldHint` | `false` |
| `readOnlyHint` | `false` |
