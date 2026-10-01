<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge_analyze_cloudwatch_logs`

**Efeito:** Só leitura: não grava nada e não acessa a rede.

## O que faz

Extrai facts do LOG do run ja coletado por `collect cloudwatch-logs`. Aceita um artefato ou o DIRETORIO deles, porque o operador que baixou `error` e `output` do mesmo run tem dois. Toda linha ja chega REDIGIDA: a redacao roda antes de o texto virar fact, e linha redigida vale `<redigido>` inteiro. Log group inexistente, sem permissao, janela vazia e sem credencial viram `cloudwatch.logs.unresolved` com a razao -- as quatro produzem a mesma lista vazia de eventos, e colapsa-las numa razao so seria uma recusa que nao nomeia nada. NAO casa assinatura: para isso existe `sparkforge_analyze_error_signatures`, que precisa da UNIAO dos facts do case.

## Parâmetros

| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `path` | string | sim | Artefato gravado por `sparkforge collect cloudwatch-logs`, ou o diretorio deles. |
| `cursor` | string | não |  |
| `detail_level` | string: `summary`, `normal`, `full` | não | Verbosidade da saida. `full` (default) devolve o fato inteiro, com a procedencia dentro de cada item -- e o modo de reauditoria. `normal` declara procedencia e `schema_version` UMA VEZ no envelope e referencia a procedencia por `provenance_ref`. `summary` reduz cada item a `id`, `kind`, `measures`, `at` (arquivo:linha) e `symbol`. Nada e apagado em silencio: o que sai do item aparece no envelope. NAO existe verbo que busque um fato por id -- para ter o fato inteiro de volta, reexecute o mesmo verbo em `full` e pague o payload inteiro outra vez. O `id` e estavel entre execucoes, entao serve para casar a linha do resumo com o mesmo fato numa execucao `full`. |
| `kind` | array de string | não |  |
| `limit` | integer | não |  |

## Na CLI

[`sparkforge analyze cloudwatch-logs`](../cli/analyze.md), [`sparkforge analyze error-signatures`](../cli/analyze.md)

## Capacidade

read the error from a run and match it against the signature catalog

## Anotações MCP

| Anotação | Valor |
|---|---|
| `destructiveHint` | `false` |
| `idempotentHint` | `true` |
| `openWorldHint` | `false` |
| `readOnlyHint` | `true` |
