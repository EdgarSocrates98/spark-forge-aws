<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge_analyze_error_signatures`

**Efeito:** Só leitura: não grava nada e não acessa a rede.

## O que faz

Casa as assinaturas de `knowledge/errors/` contra os facts do case e emite `error.signature_match` com `matched_on` (`exception_class`, `caused_by` ou `log_line`). Derivacao PURA sobre facts: nunca le artefato. A UNIAO E O CONTRATO -- o arquivo precisa trazer `spark.exception` do event log E `cloudwatch.log_event` do log, porque a recusa deste caminho e por ESCOPO e nao por linha, e metade dos facts produz um ponto cego que nao aparece. Ele NAO julga: nao devolve `likely_causes`, nem `fixes`, nem `confidence`. O juizo mora nas regras `SF-ERR-001` a `SF-ERR-006`, e cada uma exige, alem do match, o companheiro que a assinatura declara.

## Parâmetros

| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `facts_path` | string | sim | Arquivo de facts com a UNIAO do case, tipicamente produzido por `analyze event-log --out` e `analyze cloudwatch-logs --out` no mesmo arquivo. |
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
