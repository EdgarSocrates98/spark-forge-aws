<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge_analyze_athena_workgroup`

**Efeito:** Só leitura: não grava nada e não acessa a rede.

## O que faz

Extrai facts de um dump JSON de workgroups do Athena (`get_work_group`): engine version efetiva, state, bytes_scanned_cutoff. NAO chama a API do Athena -- so le o JSON ja salvo em disco (`sparkforge_collect_athena_workgroup` ou coleta manual fazem isso). Uma `effective_engine_version` sem inteiro reconhecivel (`"AUTO"`, string vazia) NUNCA vira `athena.workgroup` com valor adivinhado: vira `athena.unresolved` com `reason: unparseable_engine_version`, unico fact que desbloqueia SF-ATH-004.

## Parâmetros

| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `path` | string | sim | Arquivo ou diretorio com dumps de workgroups. |
| `cursor` | string | não |  |
| `detail_level` | string: `summary`, `normal`, `full` | não | Verbosidade da saida. `full` (default) devolve o fato inteiro, com a procedencia dentro de cada item -- e o modo de reauditoria. `normal` declara procedencia e `schema_version` UMA VEZ no envelope e referencia a procedencia por `provenance_ref`. `summary` reduz cada item a `id`, `kind`, `measures`, `at` (arquivo:linha) e `symbol`. Nada e apagado em silencio: o que sai do item aparece no envelope. NAO existe verbo que busque um fato por id -- para ter o fato inteiro de volta, reexecute o mesmo verbo em `full` e pague o payload inteiro outra vez. O `id` e estavel entre execucoes, entao serve para casar a linha do resumo com o mesmo fato numa execucao `full`. |
| `kind` | array de string | não |  |
| `limit` | integer | não |  |

## Na CLI

[`sparkforge analyze athena-workgroup`](../cli/analyze.md)

## Capacidade

extract facts from Athena workgroup configuration

## Anotações MCP

| Anotação | Valor |
|---|---|
| `destructiveHint` | `false` |
| `idempotentHint` | `true` |
| `openWorldHint` | `false` |
| `readOnlyHint` | `true` |
