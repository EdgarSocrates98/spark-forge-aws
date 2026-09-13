<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge_analyze_consumers`

**Efeito:** Só leitura: não grava nada e não acessa a rede.

## O que faz

Extrai facts do inventario DECLARADO de consumidores de tabela (`.sparkforge/consumers.yaml`, versionado com o repositorio). Unico extrator do pacote que le um arquivo escrito por uma pessoa, e de proposito: quem consome uma tabela nao esta no codigo, no plano nem no event log -- e conhecimento da organizacao. Desbloqueia SF-ENV-002 (a tabela Iceberg em format V3 que o Athena nao le). Tabela ausente do inventario nao produz fact: ausencia de declaracao nao e declaracao de ausencia.

## Parâmetros

| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `path` | string | sim | Arquivo .yaml do inventario, ou diretorio com varios. |
| `cursor` | string | não |  |
| `detail_level` | string: `summary`, `normal`, `full` | não | Verbosidade da saida. `full` (default) devolve o fato inteiro, com a procedencia dentro de cada item -- e o modo de reauditoria. `normal` declara procedencia e `schema_version` UMA VEZ no envelope e referencia a procedencia por `provenance_ref`. `summary` reduz cada item a `id`, `kind`, `measures`, `at` (arquivo:linha) e `symbol`. Nada e apagado em silencio: o que sai do item aparece no envelope. NAO existe verbo que busque um fato por id -- para ter o fato inteiro de volta, reexecute o mesmo verbo em `full` e pague o payload inteiro outra vez. O `id` e estavel entre execucoes, entao serve para casar a linha do resumo com o mesmo fato numa execucao `full`. |
| `kind` | array de string | não |  |
| `limit` | integer | não |  |

## Na CLI

[`sparkforge analyze consumers`](../cli/analyze.md)

## Capacidade

extract facts from the declared table consumer inventory

## Anotações MCP

| Anotação | Valor |
|---|---|
| `destructiveHint` | `false` |
| `idempotentHint` | `true` |
| `openWorldHint` | `false` |
| `readOnlyHint` | `true` |
