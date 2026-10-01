<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge_fuse`

**Efeito:** Só leitura: não grava nada e não acessa a rede.

## O que faz

Correlaciona facts de fontes diferentes (texto SQL de `sparkforge_analyze_sql` com schema de `sparkforge_analyze_catalog_schema`) pelo nome da tabela, e produz facts `.enriched` (`sql.projection.enriched`, `sql.predicate.enriched`) que carregam attrs das duas fontes NO MESMO fact -- o que desbloqueia SF-ATH-001, SF-ATH-002 e SF-ATH-005. `facts_paths` e repetivel de proposito: a fusao so tem o que correlacionar quando ve as duas fontes na MESMA chamada. A saida (facts originais + `.enriched` + `fusion.summary`) alimenta `sparkforge_judge` direto, sem outro passo no meio.

## Parâmetros

| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `facts_paths` | array de string | sim | Arquivos de facts (JSON) gerados por `sparkforge_analyze_*`. Repetivel: informe todas as fontes a correlacionar na mesma chamada. |
| `cursor` | string | não |  |
| `detail_level` | string: `summary`, `normal`, `full` | não | Verbosidade da saida. `full` (default) devolve o fato inteiro, com a procedencia dentro de cada item -- e o modo de reauditoria. `normal` declara procedencia e `schema_version` UMA VEZ no envelope e referencia a procedencia por `provenance_ref`. `summary` reduz cada item a `id`, `kind`, `measures`, `at` (arquivo:linha) e `symbol`. Nada e apagado em silencio: o que sai do item aparece no envelope. NAO existe verbo que busque um fato por id -- para ter o fato inteiro de volta, reexecute o mesmo verbo em `full` e pague o payload inteiro outra vez. O `id` e estavel entre execucoes, entao serve para casar a linha do resumo com o mesmo fato numa execucao `full`. |
| `kind` | array de string | não |  |
| `limit` | integer | não |  |

## Na CLI

[`sparkforge fuse`](../cli/fuse.md)

## Capacidade

correlate facts from multiple extractors before judging

## Anotações MCP

| Anotação | Valor |
|---|---|
| `destructiveHint` | `false` |
| `idempotentHint` | `true` |
| `openWorldHint` | `false` |
| `readOnlyHint` | `true` |
