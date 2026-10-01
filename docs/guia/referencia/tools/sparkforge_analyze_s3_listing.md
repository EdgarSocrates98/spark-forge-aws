<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge_analyze_s3_listing`

**Efeito:** Só leitura: não grava nada e não acessa a rede.

## O que faz

Extrai facts de um dump de `aws s3api list-objects-v2`: contagem, media, p95 e maximo de bytes por prefixo, agrupados por (formato, compressao). NAO chama a API da AWS -- so le o JSON ja salvo em disco. Desbloqueia SF-PQ-001 (small files), SF-PQ-003 (texto gzip nao splitavel) e, junto com `sparkforge_analyze_catalog_schema`, SF-PQ-005 (cardinalidade de particao). Listagem com `IsTruncated: true` NAO produz sumario: os numeros seriam de uma pagina apresentada como total, entao vira `s3.unresolved` com `reason: truncated_listing`.

## Parâmetros

| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `path` | string | sim | Arquivo .json ou diretorio com paginas da listagem. |
| `cursor` | string | não |  |
| `detail_level` | string: `summary`, `normal`, `full` | não | Verbosidade da saida. `full` (default) devolve o fato inteiro, com a procedencia dentro de cada item -- e o modo de reauditoria. `normal` declara procedencia e `schema_version` UMA VEZ no envelope e referencia a procedencia por `provenance_ref`. `summary` reduz cada item a `id`, `kind`, `measures`, `at` (arquivo:linha) e `symbol`. Nada e apagado em silencio: o que sai do item aparece no envelope. NAO existe verbo que busque um fato por id -- para ter o fato inteiro de volta, reexecute o mesmo verbo em `full` e pague o payload inteiro outra vez. O `id` e estavel entre execucoes, entao serve para casar a linha do resumo com o mesmo fato numa execucao `full`. |
| `kind` | array de string | não |  |
| `limit` | integer | não |  |

## Na CLI

[`sparkforge analyze s3-listing`](../cli/analyze.md)

## Capacidade

extract facts from an S3 object listing

## Anotações MCP

| Anotação | Valor |
|---|---|
| `destructiveHint` | `false` |
| `idempotentHint` | `true` |
| `openWorldHint` | `false` |
| `readOnlyHint` | `true` |
