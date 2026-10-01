<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge_analyze_parquet_footer`

**Efeito:** Só leitura: não grava nada e não acessa a rede.

## O que faz

Extrai facts do FOOTER de arquivos Parquet ja coletado por `collect parquet-footer`: row group, estatistica por coluna, dicionario, page index, bloom filter e codec. NAO abre arquivo Parquet -- parte do artefato JSON. A medida que so existe aqui e `avg_range_coverage`, a sobreposicao de min/max entre row groups, que separa 'sem estatistica' de 'estatistica INUTIL': cobertura perto de 1 significa que cada row group cobre quase todo o dominio e nenhum pode ser descartado, apesar de a estatistica existir. Ela e propriedade do LAYOUT e assume o predicado uniforme sobre o dominio observado -- nomeia layout que NAO PODE podar, nunca job que vai ler muito, e nao estima custo nem ganho. Onde ela nao se sustenta sai `parquet.unresolved` com a razao (`tipo_sem_dominio_numerico`, `estatistica_incompleta`, `row_group_unico`, `dominio_degenerado`). Censo parcial se anuncia: `partial: true` quando a coleta leu menos arquivos do que viu.

## Parâmetros

| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `path` | string | sim | Artefato gravado por `sparkforge collect parquet-footer`, ou o diretorio deles. |
| `cursor` | string | não |  |
| `detail_level` | string: `summary`, `normal`, `full` | não | Verbosidade da saida. `full` (default) devolve o fato inteiro, com a procedencia dentro de cada item -- e o modo de reauditoria. `normal` declara procedencia e `schema_version` UMA VEZ no envelope e referencia a procedencia por `provenance_ref`. `summary` reduz cada item a `id`, `kind`, `measures`, `at` (arquivo:linha) e `symbol`. Nada e apagado em silencio: o que sai do item aparece no envelope. NAO existe verbo que busque um fato por id -- para ter o fato inteiro de volta, reexecute o mesmo verbo em `full` e pague o payload inteiro outra vez. O `id` e estavel entre execucoes, entao serve para casar a linha do resumo com o mesmo fato numa execucao `full`. |
| `kind` | array de string | não |  |
| `limit` | integer | não |  |

## Na CLI

[`sparkforge analyze parquet-footer`](../cli/analyze.md)

## Capacidade

read the Parquet footer and measure whether its statistics can prune

## Anotações MCP

| Anotação | Valor |
|---|---|
| `destructiveHint` | `false` |
| `idempotentHint` | `true` |
| `openWorldHint` | `false` |
| `readOnlyHint` | `true` |
